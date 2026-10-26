"""Explicit opt-in rehearsal helpers for disposable, synthetic coding fixtures only."""
import csv
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import threading
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]


def run_maven(command, *, cwd, timeout):
    from run_scenarios import stop_process_tree

    process = subprocess.Popen(command, cwd=cwd, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                               start_new_session=os.name == "posix")
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except BaseException:
        stop_process_tree(process)
        raise
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def install_in_fixture(checkout):
    """Simulate joining a compatible checkout without the agent; preserve every other file."""
    checkout = checkout.resolve()
    spec = importlib.util.spec_from_file_location(
        "rehearsal_installer", ROOT / ".github/scripts/install_coding_agent.py",
    )
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)
    for relative in installer.MANAGED:
        (checkout / relative).unlink()
    before = {
        str(path.relative_to(checkout)): path.read_bytes()
        for path in checkout.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(checkout).parts
        and path.name != ".env"
    }
    plan, _ = installer.preview(checkout)
    if plan["blockers"]:
        raise ValueError("Existing-fixture installation blocked: " + "; ".join(plan["blockers"]))
    _, added = installer.apply(checkout, plan["plan_sha256"])
    if any((checkout / relative).read_bytes() != content for relative, content in before.items()):
        raise ValueError("Agent installation modified a protected fixture file")
    return {"added": added, "protected_files_unchanged": len(before),
            "plan_sha256": plan["plan_sha256"]}


def verify_http(checkout, kind, output_prefix=None):
    """Invoke the newly generated real flows deterministically, not template pattern fixtures."""
    if kind not in {"orders", "items"}:
        raise ValueError(f"Unsupported rehearsal contract: {kind}")
    if kind == "orders":
        imports = "import cz.example.perf.domain.orders.flows.OrdersFlows"
        flows = ["OrdersFlows.basicOrders()"]
        expected = Counter({"/orders": 1})
    else:
        imports = "import cz.example.perf.domain.items.flows.ItemsFlows"
        flows = ["ItemsFlows.browseItems()", "ItemsFlows.viewItemDetails()"]
        with (checkout / "src/test/resources/items/items.csv").open(encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        ids = {row.get("itemId", "") for row in rows}
        if not ids or any(not value.startswith("local-dummy-") or "/" in value for value in ids):
            raise ValueError("Rehearsal requires synthetic local-dummy-* itemId values")
        expected = Counter({"/items": 1, "<dummy-item-detail>": 1})
    calls = ",\n".join(
        f'            scenario("rehearsal-{index}").exec({flow}).injectOpen(atOnceUsers(1))'
        for index, flow in enumerate(flows)
    )
    source = f"""package cz.example.perf.contract

{imports}
import io.gatling.javaapi.core.CoreDsl.atOnceUsers
import io.gatling.javaapi.core.CoreDsl.global
import io.gatling.javaapi.core.CoreDsl.scenario
import io.gatling.javaapi.core.Simulation
import io.gatling.javaapi.http.HttpDsl.http
import java.net.URI
import java.time.Duration

class AgentRehearsalSimulation : Simulation() {{
    init {{
        val url = System.getProperty("contractBaseUrl") ?: error("Owned rehearsal mock required")
        val uri = URI(url)
        require(uri.scheme == "http" && uri.host == "127.0.0.1" && uri.port > 0)
        require(uri.rawUserInfo == null && uri.rawQuery == null && uri.rawFragment == null)
        require(uri.path.isNullOrEmpty())
        setUp(
{calls}
        ).protocols(http.baseUrl(url).disableWarmUp().disableFollowRedirect())
            .maxDuration(Duration.ofSeconds(10))
            .assertions(
                global().allRequests().count().`is`({sum(expected.values())}L),
                global().failedRequests().count().`is`(0L)
            )
    }}
}}
"""
    destination = checkout / "src/test/kotlin/cz/example/perf/contract/AgentRehearsalSimulation.kt"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as stream:
        stream.write(source)
    observed, violations = Counter(), []
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            label = self.path
            if kind == "items" and self.path.startswith("/items/") and self.path[len("/items/"):] in ids:
                label = "<dummy-item-detail>"
            valid = label in expected and self.headers.get("Content-Length", "0") == "0"
            with lock:
                observed[label] += 1
                if not valid:
                    violations.append(f"Unexpected GET/body: {self.path}")
            if label == "/items":
                payload = {"items": [{"id": next(iter(ids))}]}
            else:
                payload = {"id": self.path.rsplit("/", 1)[-1]}
            data = json.dumps(payload).encode()
            self.send_response(200 if valid else 400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    target = f"http://127.0.0.1:{server.server_port}"
    command = [
        "./mvnw", "-q", "test-compile", "gatling:test",
        "-Dgatling.simulationClass=cz.example.perf.contract.AgentRehearsalSimulation",
        f"-DcontractBaseUrl={target}", "-Dgatling.noReports=true", "-Denv=test",
    ]
    failure = None
    try:
        run = run_maven(command, cwd=checkout, timeout=240)
    except (OSError, subprocess.TimeoutExpired) as exc:
        failure = exc
        run = subprocess.CompletedProcess(command, None, "", str(exc))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        destination.unlink()
    report = {
        "passed": run.returncode == 0 and observed == expected and not violations,
        "maven_exit": run.returncode, "target": target, "max_users": len(flows), "max_duration_sec": 10,
        "expected_requests": dict(expected), "observed_requests": dict(observed),
        "wire_errors": violations, "simulation_source": source,
        "output": (run.stdout + run.stderr)[-12000:],
    }
    if failure is not None:
        report["execution_error"] = str(failure)
    if output_prefix:
        Path(f"{output_prefix}.http.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if failure is not None:
        raise failure
    return report

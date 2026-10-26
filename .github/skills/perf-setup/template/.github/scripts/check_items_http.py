"""Check sample flows and synthetic HTTP patterns on an owned loopback mock only."""
import argparse
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from collections import Counter
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[2]
SIMULATION = "src/test/kotlin/cz/example/perf/contract/ItemsHttpContractSimulation.kt"
MUTATIONS = [
    ("missing-failure-gate", SIMULATION,
     '.exitHereIfFailed()\n            .exec(\n                http("Read Created Item")',
     '.exec(\n                http("Read Created Item")'),
    ("missing-id-check", SIMULATION,
     'status().`is`(200), jsonPath("$.id").isEL("#{createdId}")', 'status().`is`(200)'),
    ("leaked-profile-header", SIMULATION,
     '.get("/public").check', '.get("/public").header("api-key", "local-dummy-key").check'),
    ("unbounded-extra-poll", SIMULATION, '.repeat(3).on(', '.repeat(4).on('),
]


def main():
    token = "local-dummy-" + uuid.uuid4().hex
    observed, errors, polls = Counter(), [], Counter()
    poll_times = {}
    expected = Counter({
        "GET /browse/items": 1, "GET /list-failure/items": 1,
        "POST /json/items": 1, f"GET /json/items/{token}": 1,
        "POST /json-wrong-id/items": 1, f"GET /json-wrong-id/items/{token}": 1,
        "POST /json-failure/items": 1, "POST /json-missing-id/items": 1,
        "POST /form/search": 1, "POST /multipart/upload": 1,
        "PUT /no-content/items/1": 1, "PATCH /no-content/items/1": 1,
        "DELETE /no-content/items/1": 1, "HEAD /no-content/items": 1,
        "OPTIONS /no-content/items": 1,
        "GET /profiles/gateway": 1, "GET /profiles/public": 1,
        "POST /poll-complete/jobs": 1, f"GET /poll-complete/jobs/{token}": 2,
        "GET /poll-complete/result": 1,
        "POST /poll-timeout/jobs": 1, f"GET /poll-timeout/jobs/{token}": 3,
        "POST /poll-terminal/jobs": 1, f"GET /poll-terminal/jobs/{token}": 1,
    })
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def handle_request(self):
            self.connection.settimeout(5)
            url = urlsplit(self.path)
            key = f"{self.command} {url.path}"
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            violations = []

            def require(condition, message):
                if not condition:
                    violations.append(f"{key}: {message}")

            content_type = self.headers.get_content_type()
            with lock:
                observed[key] += 1
                known = key in expected
            require(known, "unexpected method/path or forbidden follow-up")
            require(self.headers.get("Authorization") is None, "unexpected Authorization header")
            expected_key = "local-dummy-key" if url.path == "/profiles/gateway" else None
            require(self.headers.get("api-key") == expected_key, "API key absent or leaked between profiles")
            require(parse_qs(url.query) == ({"locale": ["en"]} if "/items/" + token in url.path else {}),
                    "incorrect query parameters")
            status, payload = 200, {}
            if self.command in {"GET", "HEAD", "DELETE", "OPTIONS"}:
                require(not body, "unexpected request body")
            if self.command in {"POST", "PUT", "PATCH"} and url.path != "/form/search" and url.path != "/multipart/upload":
                require(content_type == "application/json", "expected application/json")
                try:
                    value = json.loads(body)
                except (ValueError, UnicodeDecodeError):
                    value = None
                    require(False, "invalid JSON request body")
                expected_body = {}
                if url.path.endswith("/items"):
                    expected_body = {"name": "local-dummy-item"}
                elif self.command in {"PUT", "PATCH"}:
                    suffix = "updated" if self.command == "PUT" else "patched"
                    expected_body = {"name": f"local-dummy-{suffix}"}
                require(value == expected_body, "incorrect JSON request body")
            if url.path in {"/browse/items", "/list-failure/items"}:
                status = 500 if url.path.startswith("/list-failure") else 200
                payload = {"items": [{"id": token}]}
            elif self.command == "POST" and url.path.endswith("/items"):
                status = 500 if url.path.startswith("/json-failure") else 201
                payload = {} if url.path.startswith("/json-missing-id") else {"id": token}
            elif self.command == "GET" and "/items/" + token in url.path:
                payload = {"id": "local-dummy-wrong" if url.path.startswith("/json-wrong-id") else token}
            elif url.path == "/form/search":
                require(content_type == "application/x-www-form-urlencoded", "incorrect form Content-Type")
                require(parse_qs(body.decode("utf-8")) == {"term": ["local dummy"], "page": ["2"]},
                        "incorrect form fields/encoding")
            elif url.path == "/multipart/upload":
                require(content_type == "multipart/form-data", "incorrect multipart Content-Type")
                message = BytesParser(policy=default).parsebytes(
                    f"Content-Type: {self.headers.get('Content-Type', '')}\r\n\r\n".encode() + body
                )
                parts = list(message.iter_parts())
                require(len(parts) == 2, "expected exactly two multipart parts")
                fields = {part.get_param("name", header="content-disposition"): part for part in parts}
                require(set(fields) == {"note", "file"}, "incorrect multipart field names")
                if set(fields) == {"note", "file"}:
                    require(fields["note"].get_payload(decode=True) == b"local-dummy", "incorrect note")
                    require(fields["file"].get_payload(decode=True) == b"local-dummy-file", "incorrect file bytes")
                    require(fields["file"].get_filename() == "local-dummy.txt", "incorrect filename")
                    require(fields["file"].get_content_type() == "text/plain", "incorrect file Content-Type")
                status = 201
            elif url.path.startswith("/no-content/"):
                status = 204
            elif self.command == "POST" and url.path.endswith("/jobs"):
                status, payload = 202, {"jobId": token}
            elif "/jobs/" in url.path:
                case = url.path.split("/")[1]
                with lock:
                    polls[case] += 1
                    attempt = polls[case]
                    times = poll_times.setdefault(case, [])
                    now = time.monotonic()
                    require(not times or now - times[-1] >= 0.9, "poll interval shorter than one second")
                    times.append(now)
                state = "complete" if case == "poll-complete" and attempt == 2 else "pending"
                if case == "poll-terminal":
                    state = "failed"
                status, payload = (200 if state != "pending" else 202), {"state": state}
            if violations:
                with lock:
                    errors.extend(violations)
                status, payload = 400, {"errors": violations}
            data = b"" if status == 204 else json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Contract", "local")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = handle_request

    output = ROOT / "target/items-http-contract"
    output.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    command = [
        "./mvnw", "-q", "test-compile", "gatling:test",
        "-Dgatling.simulationClass=cz.example.perf.contract.ItemsHttpContractSimulation",
        f"-DcontractBaseUrl={url}", "-Dgatling.noReports=true", "-Denv=test",
    ]
    print(f"Owned mock: {url}; 13 users, max 15s; {sum(expected.values())} expected requests.", flush=True)
    exit_code, error = None, None
    try:
        with socket.create_connection(("127.0.0.1", server.server_port), timeout=2):
            pass
        with (output / "maven.log").open("w", encoding="utf-8") as log:
            exit_code = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                       timeout=240).returncode
    except (subprocess.TimeoutExpired, OSError) as exc:
        error = str(exc)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    passed = error is None and exit_code == 0 and observed == expected and not errors
    result = {
        "passed": passed, "maven_exit": exit_code, "error": error, "mock_url": url,
        "expected_requests": dict(expected), "observed_requests": dict(observed),
        "missing_requests": dict(expected - observed), "unexpected_requests": dict(observed - expected),
        "contract_errors": errors,
        "poll_intervals": {case: [later - earlier for earlier, later in zip(times, times[1:])]
                           for case, times in poll_times.items()},
    }
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"{'PASS' if passed else 'FAIL'}: {sum(observed.values())} HTTP requests; evidence: {output}")
    if not passed:
        print(json.dumps(result, indent=2))
        log_path = output / "maven.log"
        if log_path.exists():
            print(log_path.read_text(encoding="utf-8")[-12000:])
    return 0 if passed else 1


def check_detectors():
    outcomes = []
    for name, relative, before, after in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix="items-contract-") as tmp:
            fixture = Path(tmp)
            for directory in ("src", ".mvn", ".github"):
                shutil.copytree(ROOT / directory, fixture / directory)
            for filename in ("pom.xml", "mvnw", "detekt.yml"):
                shutil.copy2(ROOT / filename, fixture / filename)
            source = fixture / relative
            text = source.read_text(encoding="utf-8")
            if text.count(before) != 1:
                raise RuntimeError(f"{name}: expected exactly one mutation site")
            source.write_text(text.replace(before, after), encoding="utf-8")
            run = subprocess.run([sys.executable, ".github/scripts/check_items_http.py"],
                                 cwd=fixture, capture_output=True, text=True, timeout=270)
            path = fixture / "target/items-http-contract/result.json"
            if not path.is_file():
                raise RuntimeError(f"{name}: no runtime evidence:\n{run.stdout}\n{run.stderr}")
            result = json.loads(path.read_text(encoding="utf-8"))
            detected = run.returncode != 0 and bool(result["observed_requests"])
            if name == "missing-failure-gate":
                detected = detected and any("/json-failure/items/" in key
                                            for key in result["unexpected_requests"])
            elif name == "leaked-profile-header":
                detected = detected and any("API key" in error for error in result["contract_errors"])
            elif name == "unbounded-extra-poll":
                detected = detected and any("/poll-timeout/jobs/" in key
                                            for key in result["unexpected_requests"])
            else:
                log = (path.parent / "maven.log").read_text(encoding="utf-8")
                detected = detected and result["maven_exit"] != 0 and (
                    "Read Created Item: count of failed events is 1.0 : false" in log
                )
            outcomes.append({"mutation": name, "detected": detected, "evidence": result})
            print(f"{'PASS' if detected else 'FAIL'}: detector for {name}", flush=True)
    output = ROOT / "target/items-http-contract/detectors.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(outcomes, indent=2) + "\n", encoding="utf-8")
    return 0 if all(item["detected"] for item in outcomes) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-detectors", action="store_true",
                        help="verify deliberately broken contracts fail at runtime in disposable copies")
    args = parser.parse_args()
    sys.exit(check_detectors() if args.check_detectors else main())

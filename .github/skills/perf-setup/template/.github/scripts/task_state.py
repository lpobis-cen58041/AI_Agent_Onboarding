"""Local, revisioned coding-task records. Never executes checks or changes project code."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
NAME = re.compile(r"[a-z][a-z0-9_-]{0,63}")
CORE = {
    "domain_mode": "Would you like to create a new domain or extend an existing one?",
    "domain": "Which domain should this change use?",
    "change_type": "What endpoint or test change should this domain receive?",
    "acceptance": "Which concrete criteria must this change satisfy?",
    "preserve": "Which existing behavior must remain unchanged?",
}
ENDPOINT = {
    "path": "What relative endpoint path should {name} use?",
    "method": "What HTTP method should {name} use?",
    "status": "What HTTP status code should {name} return?",
    "profile": "Which existing routing/authentication profile should {name} use?",
    "path_parameters": "Where should the path-parameter values for {name} come from?",
    "query": "Which query parameters does {name} require, or are there none?",
    "body": "What request body does {name} require, or is there no body?",
    "headers": "Which additional headers does {name} require, or are there none?",
    "response": "Which response checks or extractions beyond status does {name} need?",
}
APPROVAL_QUESTION = "Shall I implement this change and run unit tests and static checks only?"
INPUTS = ("src", "ci", ".mvn", ".github", "pom.xml", "mvnw", "mvnw.cmd", "detekt.yml", "detekt.yaml",
          "README.md", "docs", ".gitignore")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def strings(value):
    return isinstance(value, list) and all(text(item) for item in value)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def decode(value):
    def invalid_constant(_):
        raise ValueError("Non-finite JSON numbers are not allowed")
    return json.loads(value, parse_constant=invalid_constant)


def input_manifest(root):
    """Hash project inputs, including untracked code/docs, but never .env or runtime state."""
    result = {}
    for name in INPUTS:
        base = root / name
        if not base.exists() and not base.is_symlink():
            continue
        require(not base.is_symlink(), f"Symlink build input is unsupported: {name}")
        paths = [base]
        if base.is_dir():
            paths = []
            for directory, dirs, files in os.walk(base, followlinks=False):
                dirs[:] = [d for d in dirs if d not in {"__pycache__", ".git"}
                           and not d.startswith(".env")]
                for child in dirs:
                    require(not (Path(directory) / child).is_symlink(), "Symlink input directory")
                paths.extend(Path(directory) / f for f in files if not f.startswith(".env"))
        for path in paths:
            require(not path.is_symlink(), "Symlink input file")
            if path.suffix == ".pyc":
                continue
            sha = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(65536), b""):
                    sha.update(chunk)
            result[str(path.relative_to(root))] = sha.hexdigest()
    return result


def code_fingerprint(root):
    return digest(input_manifest(root))


def manifest_changes(before, after):
    return {
        "added": sorted(after.keys() - before.keys()),
        "modified": sorted(path for path in before.keys() & after.keys() if before[path] != after[path]),
        "deleted": sorted(before.keys() - after.keys()),
        "unchanged": sum(before[path] == after[path] for path in before.keys() & after.keys()),
    }


def validate_generator_checks(checks, domain, task_id):
    generation = [check for check in checks if check["kind"] in ("generator-preview", "generator")]
    require([check["kind"] for check in generation] == ["generator-preview", "generator"],
            "New-domain pass needs ordered generator-preview and generator checks")
    arguments = []
    for check in generation:
        argv = shlex.split(check["command"])
        script = next((i for i, arg in enumerate(argv) if Path(arg).name == "new_domain.py"), None)
        require(script is not None, "Generator evidence must name new_domain.py")
        args = argv[script + 1:]
        require(len(args) >= 2 and args[1] == domain, "Generator evidence must name the agreed domain")
        require("--task" in args and args.index("--task") + 1 < len(args)
                and args[args.index("--task") + 1] == task_id, "Generator evidence must use the current --task")
        preview = check["kind"] == "generator-preview"
        require(args.count("--dry-run") == int(preview), "Generator preview must use --dry-run only")
        for prefix in (("would create ", "would append to ") if preview else ("created ", "appended to ")):
            require(any(line.startswith(prefix) for line in check["output"].splitlines()),
                    "Generator evidence needs actual output, not a narrative summary")
        arguments.append([arg for arg in args if arg != "--dry-run"])
    require(arguments[0] == arguments[1], "Generator preview and generation arguments must match")


def unknown(question):
    return {"status": "unknown", "value": None, "source": None, "question": question}


def value(state, key):
    return state["facts"].get(key, {}).get("value")


def endpoint_names(state):
    return sorted({key.split(".")[1] for key in state["facts"] if key.startswith("endpoint.")})


def valid_fact_key(key):
    parts = key.split(".")
    return (key in CORE or key == "mix" or re.fullmatch(r"detail\.[A-Za-z0-9_.-]{1,128}", key)
            or (len(parts) == 3 and parts[0] == "endpoint" and NAME.fullmatch(parts[1])
                and parts[2] in ENDPOINT))


def validate_fact(key, fact):
    require(valid_fact_key(key), f"Invalid fact key: {key}")
    require(isinstance(fact, dict) and set(fact) == {"status", "value", "source", "question"},
            f"Invalid fact structure: {key}")
    require(fact["status"] in {"unknown", "provided", "not_applicable"} and text(fact["question"]),
            f"Invalid fact status/question: {key}")
    if fact["status"] == "unknown":
        require(fact["value"] is None and fact["source"] is None, f"Unknown fact has a value: {key}")
        return
    require(text(fact["source"]), f"Fact requires a source: {key}")
    if fact["status"] == "not_applicable":
        optional = key.startswith("detail.") or key.endswith((".path_parameters", ".query", ".body",
                                                            ".headers", ".response")) or key == "mix"
        require(optional and fact["value"] is None, f"Fact cannot be not_applicable: {key}")
        return
    val = fact["value"]
    require(val is not None, f"Provided fact needs a value: {key}")
    if key == "domain_mode":
        require(val in ("new", "existing"), "domain_mode must be new or existing")
    elif key == "domain":
        require(isinstance(val, str) and re.fullmatch(r"[a-z][a-z0-9]*", val), "Invalid domain name")
    elif key == "change_type":
        require(val in ("endpoint", "journey", "mix", "unit"), "Invalid change_type")
    elif key == "acceptance":
        require(isinstance(val, dict) and bool(val) and all(text(k) and text(v) for k, v in val.items()),
                "acceptance must map criterion IDs to descriptions")
    elif key == "preserve":
        require(strings(val), "preserve must be a list of behavior descriptions")
    elif key == "mix":
        require(isinstance(val, dict) and bool(val) and all(text(k) and type(v) in (int, float)
                and v >= 0 for k, v in val.items()) and abs(sum(val.values()) - 100) < 1e-9,
                "mix must map unique use-case names to non-negative weights totaling 100")
    elif key.startswith("endpoint."):
        field = key.split(".")[2]
        if field == "path":
            require(isinstance(val, str) and val.startswith("/") and not val.startswith("//")
                    and "://" not in val and "\n" not in val, "Endpoint path must be relative")
        elif field == "method":
            require(val in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"), "Invalid method")
        elif field == "status":
            require(isinstance(val, list) and bool(val) and len(val) == len(set(val))
                    and all(type(n) is int and 100 <= n <= 599 for n in val), "status needs HTTP codes")


def patch_facts(state, patch):
    require(isinstance(patch, dict) and bool(patch), "patch requires a non-empty fact map")
    for key, update in patch.items():
        require(valid_fact_key(key), f"Invalid fact key: {key}")
        parts = key.split(".")
        if len(parts) == 3 and parts[0] == "endpoint":
            for field, question in ENDPOINT.items():
                state["facts"].setdefault(f"endpoint.{parts[1]}.{field}",
                                          unknown(question.format(name=parts[1])))
        require(isinstance(update, dict) and set(update) <= {"status", "value", "source", "question"},
                f"Invalid fact update: {key}")
        fact = state["facts"].setdefault(key, unknown(f"What value should {key} use?"))
        fact.update(update)
        if "value" in update and "status" not in update:
            fact["status"] = "provided"
        if fact["status"] == "unknown":
            fact.update(value=None, source=None)
        validate_fact(key, fact)
    if value(state, "domain_mode") == "new" or value(state, "change_type") in ("journey", "mix"):
        state["facts"].setdefault("mix", unknown("What percentages should the use cases receive?"))
        require(state["facts"]["mix"]["status"] != "not_applicable", "This change requires explicit mix weights")


def missing(state):
    facts = state["facts"]
    keys = ["domain_mode", "domain", "change_type"]
    for name in endpoint_names(state):
        keys.extend(f"endpoint.{name}.{field}" for field in ENDPOINT)
    keys.extend(k for k in facts if k.startswith("detail."))
    keys.extend(k for k in ("mix", "acceptance", "preserve") if k in facts)
    result = [k for k in keys if facts[k]["status"] == "unknown"]
    if value(state, "change_type") in ("endpoint", "journey") and not endpoint_names(state):
        result.insert(sum(k in result for k in ("domain_mode", "domain", "change_type")), "endpoint")
    return result


def latest(state, role):
    return next((r for r in reversed(state["reports"]) if r["role"] == role
                 and r["contract_revision"] == state["contract_revision"]), None)


def approved(state):
    return (state["intent"] == "interview" and state["approval"] is not None
            and state["approval"]["contract_revision"] == state["contract_revision"]
            and state["approval"]["decision"] == "approved" and not missing(state))


def status(state, root):
    pending = missing(state)
    manifest = input_manifest(root)
    fp = digest(manifest)
    baseline = latest(state, "baseline")
    before = baseline.get("input_manifest") if baseline else None
    result = {"id": state["id"], "goal": state["goal"], "intent": state["intent"], "revision": state["revision"],
              "contract_revision": state["contract_revision"], "code_fingerprint": fp,
              "change_summary": manifest_changes(before, manifest) if before is not None else None,
              "facts": state["facts"], "missing": pending, "next_question": None,
              "approval": state["approval"], "reports": state["reports"], "decision": state["decision"]}
    if state["intent"] == "plan_only" or (state["approval"] or {}).get("decision") == "declined":
        phase = "on_hold"
    elif pending:
        phase = "intake"
        first = pending[0]
        result["next_question"] = ("What relative endpoint path should the request use?" if first == "endpoint"
                                   else state["facts"][first]["question"])
    elif not approved(state):
        phase = "awaiting_approval"
        result["next_question"] = APPROVAL_QUESTION
    else:
        baseline, coder, reviewer = (latest(state, role) for role in ("baseline", "coder", "reviewer"))
        if not baseline:
            phase = "baseline"
        elif baseline["outcome"] != "pass":
            phase = "blocked"
        elif not coder:
            phase = "implement"
        elif coder["code_fingerprint"] != fp:
            phase = "stale_code"
        elif coder["outcome"] != "pass":
            phase = "blocked"
        elif not reviewer or reviewer["based_on"] != coder["id"] or reviewer["code_fingerprint"] != fp:
            phase = "review"
        elif reviewer["outcome"] != "pass":
            phase = "blocked"
        elif state["decision"] and state["decision"]["report_id"] == reviewer["id"]:
            phase = "accepted"
        else:
            phase = "ready_to_accept"
    result["phase"] = phase
    return result


def report(state, data, root):
    fields = {"role", "worker_id", "outcome", "summary", "checks", "boundary",
              "unverified", "blockers", "criteria", "based_on", "code_fingerprint"}
    require(isinstance(data, dict) and set(data) <= fields, "Invalid report fields")
    require(approved(state), "Current contract has not been approved")
    role = data.get("role")
    require(role in ("baseline", "coder", "reviewer"), "Invalid report role")
    require(text(data.get("worker_id")) and text(data.get("summary")), "Report needs worker_id and summary")
    require(data.get("outcome") in ("pass", "fail", "blocked"), "Invalid report outcome")
    require(strings(data.get("boundary")) and strings(data.get("unverified"))
            and strings(data.get("blockers")), "Report needs boundary, unverified and blockers lists")
    checks = data.get("checks")
    require(isinstance(checks, list), "Report needs checks")
    for check in checks:
        require(isinstance(check, dict) and set(check) == {"kind", "command", "exit_code", "output"},
                "Each check needs kind, command, exit_code and output")
        require(check["kind"] in ("unit", "static", "generator-preview", "generator")
                and text(check["command"]) and text(check["output"])
                and type(check["exit_code"]) is int, "Invalid code-only check evidence")
    manifest = input_manifest(root)
    fp = digest(manifest)
    require(data.get("code_fingerprint") == fp, "Report fingerprint is not the current code")
    if data["outcome"] == "pass":
        required = {"unit"} if role == "baseline" else {"unit", "static"}
        require(required <= {c["kind"] for c in checks} and all(c["exit_code"] == 0 for c in checks)
                and not data["blockers"], "Passing report needs successful checks and no blockers")
    if role == "baseline":
        require(latest(state, "coder") is None, "Do not replace pre-edit baseline after a coder report")
        require(state["approval"].get("code_fingerprint") == fp,
                "Code changed since approval; cannot reconstruct a pre-edit baseline")
        previous = latest(state, "baseline")
        require(previous is None or previous["outcome"] != "pass" or previous["code_fingerprint"] == fp,
                "Do not replace a passing pre-edit baseline after code changes")
    if role == "coder":
        baseline = latest(state, "baseline")
        require(baseline is not None and baseline["outcome"] == "pass"
                and data.get("based_on") == baseline["id"], "Coder report needs the passing baseline ID")
        if data["outcome"] == "pass" and value(state, "domain_mode") == "new":
            validate_generator_checks(checks, value(state, "domain"), state["id"])
    if role == "reviewer":
        coder = latest(state, "coder")
        require(coder is not None and data.get("based_on") == coder["id"]
                and coder["code_fingerprint"] == fp, "Review must reference the current coder report/code")
        require(data["worker_id"] not in {r["worker_id"] for r in state["reports"] if r["role"] == "coder"},
                "Reviewer must be independent of every coder on this task")
        require(isinstance(data.get("criteria"), dict)
                and set(data["criteria"]) == set(value(state, "acceptance")),
                "Reviewer must assess every acceptance criterion")
        require(all(v in ("pass", "fail", "unverified") for v in data["criteria"].values()),
                "Invalid criterion result")
        if data["outcome"] == "pass":
            require(coder["outcome"] == "pass" and all(v == "pass" for v in data["criteria"].values()),
                    "Build success alone cannot satisfy unverified acceptance criteria")
    record = copy.deepcopy(data)
    if role == "baseline":
        record["input_manifest"] = manifest
    record.update(id=len(state["reports"]) + 1, contract_revision=state["contract_revision"])
    state["reports"].append(record)
    state["decision"] = None


def task_path(root, task_id):
    require(NAME.fullmatch(task_id), "Task ID must be a lowercase slug of at most 64 characters")
    folder = root / ".perf-coding" / "tasks"
    require(not folder.parent.is_symlink() and not folder.is_symlink(), "State directory cannot be a symlink")
    path = folder / f"{task_id}.json"
    require(not path.is_symlink(), "State file cannot be a symlink")
    return path


def load(path):
    state = decode(path.read_text(encoding="utf-8"))
    require(isinstance(state, dict) and type(state.get("schema_version")) is int
            and state["schema_version"] == 1, "Unsupported task schema")
    require(state.get("id") == path.stem and type(state.get("revision")) is int, "Invalid task identity/revision")
    require(type(state.get("contract_revision")) is int and state["contract_revision"] >= 1
            and state["revision"] >= 1 and text(state.get("goal"))
            and state.get("intent") in ("interview", "plan_only"), "Invalid task metadata")
    require(isinstance(state.get("facts"), dict) and set(CORE) <= set(state["facts"])
            and isinstance(state.get("reports"), list) and isinstance(state.get("history"), list)
            and "approval" in state and "decision" in state, "Incomplete task record")
    for key, fact in state["facts"].items():
        validate_fact(key, fact)
    return state


def generation_task(root, domain, task_id=None):
    """Prevent an active coding task from generating before its recorded baseline."""
    if task_id is None:
        folder = task_path(root, "generation").parent
        for path in folder.glob("*.json"):
            candidate = load(task_path(root, path.stem))
            if approved(candidate) and value(candidate, "domain_mode") == "new" and value(candidate, "domain") == domain:
                raise ValueError(f"Active coding task requires --task {candidate['id']} and a passing baseline")
        return None
    state = load(task_path(root, task_id))
    require(approved(state) and value(state, "domain_mode") == "new" and value(state, "domain") == domain,
            "Generator needs an approved new-domain task for the requested domain")
    baseline = latest(state, "baseline")
    require(baseline is not None and baseline["outcome"] == "pass",
            "Record a passing baseline before running the generator")
    require(code_fingerprint(root) == baseline["code_fingerprint"],
            "Code changed since baseline; do not regenerate or reconstruct earlier evidence")
    return state


def apply(root, task_id, action, revision=None, data=None):
    path = task_path(root, task_id)
    if action == "show":
        return status(load(path), root)
    if action == "validate-report":
        state = load(path)
        require(type(revision) is int and revision == state["revision"], "Stale revision; read show before validating")
        report(state, data, root)
        return {"id": task_id, "revision": revision, "valid": True}
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(".lock")
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError("Task is locked; do not retry a live writer. Inspect the writer before removing a stale lock.") from exc
    os.close(descriptor)
    temporary = None
    try:
        if action == "init":
            require(not path.exists(), "Task already exists; choose it explicitly or use a new ID")
            require(isinstance(data, dict) and set(data) == {"goal", "intent"} and text(data["goal"])
                    and data["intent"] in ("interview", "plan_only"), "init needs goal and intent")
            state = {"schema_version": 1, "id": task_id, "revision": 0, "contract_revision": 1,
                     **data, "facts": {key: unknown(question) for key, question in CORE.items()},
                     "approval": None, "reports": [], "decision": None, "history": []}
        else:
            state = load(path)
            require(type(revision) is int and revision == state["revision"], "Stale revision; read show before updating")
            if action == "patch":
                previous = copy.deepcopy(state["facts"])
                patch_facts(state, data)
                if previous != state["facts"]:
                    state["contract_revision"] += 1
                    state["approval"] = None
                    state["decision"] = None
            elif action in ("approve", "decline"):
                require(isinstance(data, dict) and set(data) == {"source"} and text(data["source"]),
                        "Approval/decline needs the actual user decision source")
                if action == "approve":
                    require(not missing(state) and state["intent"] == "interview",
                            "Cannot approve an incomplete or plan-only task")
                state["approval"] = {"decision": "approved" if action == "approve" else "declined",
                                     "contract_revision": state["contract_revision"], **data}
                if action == "approve":
                    state["approval"]["code_fingerprint"] = code_fingerprint(root)
                if action == "decline":
                    state["intent"] = "plan_only"
                state["decision"] = None
            elif action == "intent":
                require(isinstance(data, dict) and set(data) == {"intent", "source"}
                        and data["intent"] in ("interview", "plan_only") and text(data["source"]), "Invalid intent")
                state["intent"] = data["intent"]
                state["approval"] = None
                state["decision"] = None
            elif action == "report":
                report(state, data, root)
            elif action == "accept":
                require(status(state, root)["phase"] == "ready_to_accept", "Current independent evidence is not acceptable")
                require(isinstance(data, dict) and set(data) == {"reason"} and text(data["reason"]), "Acceptance needs a reason")
                state["decision"] = {"report_id": latest(state, "reviewer")["id"], **data}
            else:
                raise ValueError("Unknown state action")
        state["revision"] += 1
        state["history"].append({"revision": state["revision"], "contract_revision": state["contract_revision"],
                                 "action": action, "at": datetime.now(timezone.utc).isoformat()})
        result = status(state, root)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(state, stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        return result
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
        lock.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("init", "show", "patch", "approve", "decline", "intent",
                                          "report", "validate-report", "accept"))
    parser.add_argument("task_id")
    parser.add_argument("--revision", type=int)
    parser.add_argument("--data", help="JSON facts, report or decision; synthetic data only")
    args = parser.parse_args(argv)
    try:
        result = apply(ROOT, args.task_id, args.action, args.revision,
                       decode(args.data) if args.data is not None else None)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"ERROR: task state: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

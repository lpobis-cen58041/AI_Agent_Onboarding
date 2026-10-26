"""Task bookkeeping and acceptance gates without model calls, credentials or HTTP."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / ".github/skills/perf-setup/template/.github/scripts/task_state.py"
spec = importlib.util.spec_from_file_location("task_state", SCRIPT)
state = importlib.util.module_from_spec(spec)
spec.loader.exec_module(state)


def provided(value, source="user"):
    return {"value": value, "source": source}


def create(root):
    (root / "src").mkdir(exist_ok=True)
    (root / "src/request.kt").write_text("original")
    return state.apply(root, "summary", "init", data={"goal": "Add one request", "intent": "interview"})


def change(root, action, data=None):
    revision = state.apply(root, "summary", "show")["revision"]
    return state.apply(root, "summary", action, revision, data)


def ready(root):
    create(root)
    return change(root, "patch", {
        "domain_mode": provided("existing"), "domain": provided("items"), "change_type": provided("endpoint"),
        "endpoint.summary.path": provided("/items/summary"), "endpoint.summary.method": provided("GET"),
        "endpoint.summary.status": provided([200]), "endpoint.summary.profile": provided("existing dummy profile"),
        "endpoint.summary.path_parameters": provided([]), "endpoint.summary.query": provided([]),
        "endpoint.summary.body": provided({"format": "none"}), "endpoint.summary.headers": provided([]),
        "endpoint.summary.response": provided({"format": "status_only"}),
        "acceptance": provided({"status": "GET summary expects 200", "preserve": "Existing mix is unchanged"}),
        "preserve": provided(["Existing mix and injection"]),
    })


def evidence(root, role, worker, based_on=None, outcome="pass"):
    checks = [{"kind": kind, "command": "example validation command", "exit_code": 0, "output": "fixture output"}
              for kind in (["unit"] if role == "baseline" else ["unit", "static"])]
    result = {"role": role, "worker_id": worker, "outcome": outcome, "summary": "Synthetic test fixture",
              "checks": checks, "boundary": ["src/request.kt"], "unverified": ["HTTP behavior"],
              "blockers": [], "code_fingerprint": state.code_fingerprint(root)}
    if based_on is not None:
        result["based_on"] = based_on
    if role == "reviewer":
        result["criteria"] = {"status": "pass", "preserve": "pass"}
    return result


def reviewed(root):
    ready(root)
    change(root, "approve", {"source": "user: implement with unit/static checks only"})
    change(root, "report", evidence(root, "baseline", "coder-1"))
    (root / "src/request.kt").write_text("updated")
    change(root, "report", evidence(root, "coder", "coder-1", 1))
    return change(root, "report", evidence(root, "reviewer", "reviewer-1", 2))


def new_domain_ready(root):
    ready(root)
    change(root, "patch", {"domain_mode": provided("new"), "domain": provided("orders"),
                           "mix": provided({"basicOrders": 100})})
    change(root, "approve", {"source": "user: generate orders, unit/static only"})
    return change(root, "report", evidence(root, "baseline", "coder-1"))


def generator_checks():
    command = "python3 .github/scripts/new_domain.py . orders --path /orders --method GET --task summary"
    return [
        {"kind": "generator-preview", "command": command + " --dry-run", "exit_code": 0,
         "output": "would create src/orders.kt\nwould append to ci/simulation-data.csv: orders"},
        {"kind": "generator", "command": command, "exit_code": 0,
         "output": "created src/orders.kt\nappended to ci/simulation-data.csv: orders"},
    ]


def test_baseline_retains_manifest_and_reports_changes_without_git(tmp_path):
    (tmp_path / "README.md").write_text("original documentation")
    baseline = new_domain_ready(tmp_path)
    manifest = baseline["reports"][0]["input_manifest"]
    assert set(manifest) == {"src/request.kt", "README.md"}
    assert baseline["change_summary"] == {"added": [], "modified": [], "deleted": [], "unchanged": 2}
    (tmp_path / "src/orders.kt").write_text("new domain")
    (tmp_path / "README.md").write_text("updated documentation")
    (tmp_path / "src/request.kt").unlink()
    result = state.apply(tmp_path, "summary", "show")
    assert result["reports"][0]["input_manifest"] == manifest
    assert result["change_summary"] == {
        "added": ["src/orders.kt"], "modified": ["README.md"], "deleted": ["src/request.kt"], "unchanged": 0,
    }
    assert not (tmp_path / ".git").exists()


def test_passing_baseline_cannot_be_replaced_after_unreported_edits(tmp_path):
    new_domain_ready(tmp_path)
    (tmp_path / "src/request.kt").write_text("edited after baseline")
    before = state.task_path(tmp_path, "summary").read_bytes()
    with pytest.raises(ValueError, match="pre-edit baseline"):
        change(tmp_path, "report", evidence(tmp_path, "baseline", "coder-1"))
    assert state.task_path(tmp_path, "summary").read_bytes() == before


def test_first_baseline_cannot_be_reconstructed_after_edits(tmp_path):
    ready(tmp_path)
    change(tmp_path, "approve", {"source": "user: implement"})
    (tmp_path / "src/request.kt").write_text("edited before baseline report")
    with pytest.raises(ValueError, match="Code changed since approval"):
        change(tmp_path, "report", evidence(tmp_path, "baseline", "coder-1"))


def test_generation_requires_approved_task_and_unchanged_passing_baseline(tmp_path):
    assert state.generation_task(tmp_path, "orders") is None
    ready(tmp_path)
    change(tmp_path, "patch", {"domain_mode": provided("new"), "domain": provided("orders"),
                              "mix": provided({"basicOrders": 100})})
    with pytest.raises(ValueError, match="approved new-domain"):
        state.generation_task(tmp_path, "orders", "summary")
    change(tmp_path, "approve", {"source": "user: implement"})
    with pytest.raises(ValueError, match="--task summary"):
        state.generation_task(tmp_path, "orders")
    with pytest.raises(ValueError, match="passing baseline"):
        state.generation_task(tmp_path, "orders", "summary")
    change(tmp_path, "report", evidence(tmp_path, "baseline", "coder-1"))
    assert state.generation_task(tmp_path, "orders", "summary")["id"] == "summary"
    assert state.generation_task(tmp_path, "another") is None
    (tmp_path / "src/request.kt").write_text("edited after baseline")
    with pytest.raises(ValueError, match="changed since baseline"):
        state.generation_task(tmp_path, "orders", "summary")


def test_standalone_generation_does_not_limit_domain_to_task_id_length(tmp_path):
    assert state.generation_task(tmp_path, "domain" * 15) is None
    assert not (tmp_path / ".perf-coding").exists()


@pytest.mark.parametrize("defect", [None, "wrong-parent", "extra-field", "missing-summary", "stale-revision"])
def test_review_validation_is_read_only_and_rejects_malformed_handoffs(tmp_path, defect):
    ready(tmp_path)
    change(tmp_path, "approve", {"source": "user: implement"})
    change(tmp_path, "report", evidence(tmp_path, "baseline", "coder-1"))
    current = change(tmp_path, "report", evidence(tmp_path, "coder", "coder-1", 1))
    candidate = evidence(tmp_path, "reviewer", "reviewer-1", 2)
    revision = current["revision"]
    if defect == "wrong-parent":
        candidate["based_on"] = 1
    elif defect == "extra-field":
        candidate["coder_report_id"] = 2
    elif defect == "missing-summary":
        del candidate["summary"]
    elif defect == "stale-revision":
        revision -= 1
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    if defect:
        with pytest.raises(ValueError):
            state.apply(tmp_path, "summary", "validate-report", revision, candidate)
    else:
        assert state.apply(tmp_path, "summary", "validate-report", revision, candidate) == {
            "id": "summary", "revision": revision, "valid": True,
        }
    after = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after
    assert state.apply(tmp_path, "summary", "show")["phase"] == "review"
    assert not state.task_path(tmp_path, "summary").with_suffix(".lock").exists()


def test_real_generator_respects_task_guard_without_creating_partial_domain(tmp_path):
    scripts = tmp_path / ".github/scripts"
    scripts.mkdir(parents=True)
    for name in ("new_domain.py", "task_state.py"):
        (scripts / name).write_bytes(SCRIPT.with_name(name).read_bytes())
    marker = tmp_path / "src/main/kotlin/cz/example/perf/setup/UseCase.kt"
    marker.parent.mkdir(parents=True)
    marker.write_text("package cz.example.perf.setup\n")
    for rel, content in (("src/main/resources/env/test.properties", ""),
                         ("src/main/resources/env/prod.properties", ""),
                         ("ci/simulation-data.csv", "simulation,source,target\n")):
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    new_domain_ready(tmp_path)
    command = [sys.executable, str(scripts / "new_domain.py"), str(tmp_path), "orders"]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 1 and "--task summary" in result.stderr
    domain = marker.parents[1] / "domain/orders"
    assert not domain.exists()
    before = state.code_fingerprint(tmp_path)
    preview = subprocess.run(command + ["--task", "summary", "--dry-run"], capture_output=True, text=True)
    assert preview.returncode == 0, preview.stderr
    assert state.code_fingerprint(tmp_path) == before and not domain.exists()
    generated = subprocess.run(command + ["--task", "summary"], capture_output=True, text=True)
    assert generated.returncode == 0, generated.stderr
    assert domain.is_dir() and (tmp_path / "docs/orders.md").is_file()
    after = state.code_fingerprint(tmp_path)
    repeated = subprocess.run(command + ["--task", "summary"], capture_output=True, text=True)
    assert repeated.returncode == 1 and "changed since baseline" in repeated.stderr
    assert state.code_fingerprint(tmp_path) == after


@pytest.mark.parametrize("defect", [
    "missing", "reversed", "different-domain", "different-path", "no-preview-flag", "narrative-only", "no-task",
])
def test_new_domain_requires_ordered_matching_generator_evidence(tmp_path, defect):
    new_domain_ready(tmp_path)
    checks = generator_checks()
    if defect == "missing":
        checks = []
    elif defect == "reversed":
        checks.reverse()
    elif defect == "different-domain":
        for check in checks:
            check["command"] = check["command"].replace("orders", "items")
    elif defect == "different-path":
        checks[1]["command"] = checks[1]["command"].replace("/orders", "/other")
    elif defect == "no-preview-flag":
        checks[0]["command"] = checks[1]["command"]
    elif defect == "no-task":
        for check in checks:
            check["command"] = check["command"].replace(" --task summary", "")
    else:
        checks[0]["output"] = "Preview ran successfully."
    report = evidence(tmp_path, "coder", "coder-1", 1)
    report["checks"] = checks + report["checks"]
    before = state.task_path(tmp_path, "summary").read_bytes()
    with pytest.raises(ValueError, match="[Gg]enerator"):
        change(tmp_path, "report", report)
    assert state.task_path(tmp_path, "summary").read_bytes() == before


def test_new_domain_accepts_reported_generator_evidence_and_independent_review(tmp_path):
    new_domain_ready(tmp_path)
    (tmp_path / "src/orders.kt").write_text("generated domain")
    report = evidence(tmp_path, "coder", "coder-1", 1)
    report["checks"] = generator_checks() + report["checks"]
    result = change(tmp_path, "report", report)
    assert result["reports"][-1]["checks"][:2] == generator_checks()
    assert result["phase"] == "review"
    result = change(tmp_path, "report", evidence(tmp_path, "reviewer", "reviewer-1", 2))
    assert result["phase"] == "ready_to_accept"
    assert change(tmp_path, "accept", {"reason": "Reviewed reported evidence"})["phase"] == "accepted"


def test_documentation_edits_invalidate_accepted_evidence(tmp_path):
    reviewed(tmp_path)
    change(tmp_path, "accept", {"reason": "Reviewed evidence"})
    (tmp_path / "README.md").write_text("changed after review")
    assert state.apply(tmp_path, "summary", "show")["phase"] == "stale_code"


def test_unknown_facts_persist_and_next_question_is_explicit(tmp_path):
    result = create(tmp_path)
    assert result["phase"] == "intake"
    assert result["next_question"].endswith("?")
    result = change(tmp_path, "patch", {"domain_mode": provided("existing"), "domain": provided("items"),
                                      "change_type": provided("endpoint")})
    assert result["missing"][0] == "endpoint"
    assert "endpoint path" in result["next_question"]
    result = change(tmp_path, "patch", {"endpoint.summary.path": provided("/items/{id}")})
    assert result["missing"][0] == "endpoint.summary.method"
    assert result["facts"]["domain"]["source"] == "user"
    assert state.apply(tmp_path, "summary", "show") == result


def test_complete_contract_asks_approval_not_more_parameters(tmp_path):
    result = ready(tmp_path)
    assert result["phase"] == "awaiting_approval"
    assert result["next_question"] == state.APPROVAL_QUESTION
    assert result["approval"] is None
    assert change(tmp_path, "approve", {"source": "user: yes"})["phase"] == "baseline"


def test_correction_invalidates_confirmation_and_reports_but_preserves_history(tmp_path):
    reviewed(tmp_path)
    result = change(tmp_path, "patch", {"endpoint.summary.status": provided([204], "user correction")})
    assert result["phase"] == "awaiting_approval"
    assert result["approval"] is None and len(result["reports"]) == 3
    assert result["facts"]["endpoint.summary.path"]["value"] == "/items/summary"
    change(tmp_path, "approve", {"source": "user: accept revised contract"})
    assert state.apply(tmp_path, "summary", "show")["phase"] == "baseline"
    with pytest.raises(ValueError, match="not acceptable"):
        change(tmp_path, "accept", {"reason": "Old checks passed"})


def test_plan_only_and_declined_tasks_remain_on_hold_after_corrections(tmp_path):
    ready(tmp_path)
    change(tmp_path, "decline", {"source": "user: leave it as a plan"})
    result = change(tmp_path, "patch", {"endpoint.summary.status": provided([204])})
    assert result["phase"] == "on_hold" and result["next_question"] is None
    with pytest.raises(ValueError, match="plan-only"):
        change(tmp_path, "approve", {"source": "not a user resume"})
    result = change(tmp_path, "intent", {"intent": "interview", "source": "user: resume"})
    assert result["phase"] == "awaiting_approval"


def test_acceptance_needs_distinct_reviewer_and_current_code(tmp_path):
    result = reviewed(tmp_path)
    assert result["phase"] == "ready_to_accept"
    assert change(tmp_path, "accept", {"reason": "Reviewed criteria and both reports"})["phase"] == "accepted"
    (tmp_path / "src/request.kt").write_text("edited after checks")
    assert state.apply(tmp_path, "summary", "show")["phase"] == "stale_code"
    with pytest.raises(ValueError, match="not acceptable"):
        change(tmp_path, "accept", {"reason": "Prior reviewer passed"})


@pytest.mark.parametrize("defect", ["same-worker", "missing-criterion", "unverified-criterion",
                                   "failed-check", "missing-static", "stale-code", "wrong-coder"])
def test_rejects_insufficient_review_without_changing_state(tmp_path, defect):
    reviewed(tmp_path)
    report = evidence(tmp_path, "reviewer", "reviewer-2", 2)
    if defect == "same-worker":
        report["worker_id"] = "coder-1"
    elif defect == "missing-criterion":
        del report["criteria"]["preserve"]
    elif defect == "unverified-criterion":
        report["criteria"]["status"] = "unverified"
    elif defect == "failed-check":
        report["checks"][0]["exit_code"] = 1
    elif defect == "missing-static":
        report["checks"].pop()
    elif defect == "stale-code":
        report["code_fingerprint"] = "obsolete"
    else:
        report["based_on"] = 99
    path = state.task_path(tmp_path, "summary")
    before = path.read_bytes()
    with pytest.raises(ValueError):
        change(tmp_path, "report", report)
    assert path.read_bytes() == before
    assert not path.with_suffix(".lock").exists()


def test_failing_baseline_is_a_blocker_not_success_shaped_fallback(tmp_path):
    ready(tmp_path)
    change(tmp_path, "approve", {"source": "user: yes"})
    baseline = evidence(tmp_path, "baseline", "coder-1", outcome="fail")
    baseline["checks"][0]["exit_code"] = 1
    baseline["blockers"] = ["Compilation failed"]
    assert change(tmp_path, "report", baseline)["phase"] == "blocked"
    with pytest.raises(ValueError, match="baseline"):
        change(tmp_path, "report", evidence(tmp_path, "coder", "coder-1", 1))


def test_reports_cannot_start_before_approval_or_replace_preedit_baseline(tmp_path):
    ready(tmp_path)
    with pytest.raises(ValueError, match="not been approved"):
        change(tmp_path, "report", evidence(tmp_path, "baseline", "coder-1"))
    change(tmp_path, "approve", {"source": "user: yes"})
    change(tmp_path, "report", evidence(tmp_path, "baseline", "coder-1"))
    change(tmp_path, "report", evidence(tmp_path, "coder", "coder-1", 1))
    with pytest.raises(ValueError, match="pre-edit baseline"):
        change(tmp_path, "report", evidence(tmp_path, "baseline", "coder-1"))


@pytest.mark.parametrize("key,val", [
    ("domain_mode", "unknown-mode"), ("endpoint.summary.method", "MAGIC"),
    ("endpoint.summary.status", [True]), ("endpoint.summary.status", [600]),
    ("endpoint.summary.path", "//example.test"), ("endpoint.summary.path", "https://example.test"),
    ("mix", {"browse": 60, "detail": 30}), ("mix", {"browse": -1, "detail": 101}),
])
def test_invalid_facts_are_rejected_atomically(tmp_path, key, val):
    ready(tmp_path)
    before = state.task_path(tmp_path, "summary").read_bytes()
    with pytest.raises(ValueError):
        change(tmp_path, "patch", {key: provided(val)})
    assert state.task_path(tmp_path, "summary").read_bytes() == before


def test_required_mix_cannot_be_skipped(tmp_path):
    ready(tmp_path)
    change(tmp_path, "patch", {"change_type": provided("journey")})
    with pytest.raises(ValueError, match="mix weights"):
        change(tmp_path, "patch", {"mix": {"status": "not_applicable", "value": None, "source": "guess"}})
    assert "mix" in change(tmp_path, "patch", {"detail.risk": {
        "status": "unknown", "question": "Which risk level does the contract specify?"}})["missing"]


def test_stale_revision_lock_and_duplicate_init_preserve_record(tmp_path):
    initial = create(tmp_path)
    change(tmp_path, "patch", {"domain": provided("items")})
    path = state.task_path(tmp_path, "summary")
    before = path.read_bytes()
    with pytest.raises(ValueError, match="Stale revision"):
        state.apply(tmp_path, "summary", "patch", initial["revision"], {"domain": provided("orders")})
    with pytest.raises(ValueError, match="already exists"):
        create(tmp_path)
    lock = path.with_suffix(".lock")
    lock.touch()
    with pytest.raises(ValueError, match="locked"):
        change(tmp_path, "patch", {"domain": provided("orders")})
    assert lock.exists() and path.read_bytes() == before
    lock.unlink()


def test_fingerprint_ignores_state_build_output_and_env_and_rejects_symlinks(tmp_path, monkeypatch):
    create(tmp_path)
    before = state.code_fingerprint(tmp_path)
    (tmp_path / "src/.env").write_text("must not be read")
    (tmp_path / "target").mkdir()
    (tmp_path / "target/report.txt").write_text("generated")
    original_open = Path.open

    def checked_open(path, *args, **kwargs):
        assert not path.name.startswith(".env"), "Secret file must never be opened"
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", checked_open)
    assert state.code_fingerprint(tmp_path) == before
    (tmp_path / "src/alias").symlink_to(tmp_path / "src/.env")
    with pytest.raises(ValueError, match="Symlink"):
        state.code_fingerprint(tmp_path)


def test_concurrent_writers_cannot_overwrite_each_other(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    revision = create(tmp_path)["revision"]
    barrier = Barrier(2)

    def write(domain):
        barrier.wait()
        try:
            return state.apply(tmp_path, "summary", "patch", revision, {"domain": provided(domain)})
        except ValueError as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, ("items", "orders")))
    assert sum(isinstance(result, dict) for result in results) == 1
    assert state.apply(tmp_path, "summary", "show")["revision"] == revision + 1
    assert len(list((tmp_path / ".perf-coding/tasks").iterdir())) == 1


def test_failed_semantic_review_blocks_acceptance_despite_passing_builds(tmp_path):
    reviewed(tmp_path)
    review = evidence(tmp_path, "reviewer", "reviewer-2", 2, outcome="fail")
    review["criteria"]["preserve"] = "fail"
    review["blockers"] = ["Unrelated behavior changed"]
    result = change(tmp_path, "report", review)
    assert result["phase"] == "blocked"
    with pytest.raises(ValueError, match="not acceptable"):
        change(tmp_path, "accept", {"reason": "But all build commands passed"})


@pytest.mark.parametrize("corruption", ["schema", "missing-core", "invalid-fact"])
def test_corrupt_records_fail_explicitly(tmp_path, corruption):
    create(tmp_path)
    path = state.task_path(tmp_path, "summary")
    data = json.loads(path.read_text())
    if corruption == "schema":
        data["schema_version"] = True
    elif corruption == "missing-core":
        del data["facts"]["domain"]
    else:
        data["facts"]["endpoint.broken"] = state.unknown("What is missing?")
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        state.apply(tmp_path, "summary", "show")


def test_path_traversal_and_symlink_state_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="Task ID"):
        state.apply(tmp_path, "../escape", "init")
    (tmp_path / ".perf-coding").symlink_to(tmp_path)
    with pytest.raises(ValueError, match="symlink"):
        create(tmp_path)


def test_cli_persists_across_fresh_processes_and_reports_errors(tmp_path):
    script = tmp_path / ".github/scripts/task_state.py"
    script.parent.mkdir(parents=True)
    script.write_bytes(SCRIPT.read_bytes())
    command = [sys.executable, str(script)]
    result = subprocess.run(command + ["init", "sample", "--data", json.dumps({
        "goal": "Persist task", "intent": "interview"})], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    result = subprocess.run(command + ["show", "sample"], capture_output=True, text=True)
    assert json.loads(result.stdout)["next_question"].endswith("?")
    result = subprocess.run(command + ["patch", "sample", "--revision", "0", "--data", "{}"],
                            capture_output=True, text=True)
    assert result.returncode == 1 and "Stale revision" in result.stderr and not result.stdout
    assert len(list((tmp_path / ".perf-coding/tasks").iterdir())) == 1

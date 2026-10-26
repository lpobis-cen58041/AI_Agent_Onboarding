"""Packaging checks for the optional loopback suite; no HTTP or model calls."""
import importlib.util
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / ".github/skills/perf-setup/template"
CHECKER = TEMPLATE / ".github/scripts/check_items_http.py"
SIMULATION = "src/test/kotlin/cz/example/perf/contract/ItemsHttpContractSimulation.kt"


def test_explicit_demo_scaffold_contains_reproducible_http_check(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / ".github/scripts/scaffold.py"), "http-fixture",
         "--dest", str(tmp_path), "--no-test", "--no-git", "--demo"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    fixture = tmp_path / "http-fixture"
    for path in (".github/scripts/check_items_http.py", SIMULATION,
                 "src/test/kotlin/cz/example/perf/config/ArrivalRateTest.kt"):
        assert (fixture / path).read_bytes() == (TEMPLATE / path).read_bytes()
    assert "27 expected requests" in (fixture / "README.md").read_text()
    assert "__PROJECT_NAME__" not in (fixture / "README.md").read_text()
    assert not (fixture / ".git").exists()


def test_each_detector_targets_exactly_one_site_in_shipped_source():
    spec = importlib.util.spec_from_file_location("template_http", CHECKER)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    mutations = checker.MUTATIONS
    assert {mutation[0] for mutation in mutations} == {
        "missing-failure-gate", "missing-id-check", "leaked-profile-header", "unbounded-extra-poll",
    }
    for name, relative, before, after in mutations:
        assert (TEMPLATE / relative).read_text().count(before) == 1, name
        assert before != after


def test_optional_http_execution_is_gated_in_both_workflows():
    for path in (ROOT / ".github/workflows/test.yml", TEMPLATE / ".github/workflows/DemoHttp.yml"):
        workflow = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
        dispatch = workflow["on"]["workflow_dispatch"]["inputs"]["local_http"]
        assert dispatch["default"] == "false"
        steps = next(iter(workflow["jobs"].values()))["steps"]
        http_steps = [step for step in steps if "check_items_http.py" in step.get("run", "")]
        assert len(http_steps) == 1
        assert http_steps[0]["if"] == "github.event_name == 'workflow_dispatch' && inputs.local_http"
    regular = (TEMPLATE / ".github/workflows/PRCheck.yml").read_text()
    assert "check_items_http.py" not in regular
    assert "local_http" not in regular

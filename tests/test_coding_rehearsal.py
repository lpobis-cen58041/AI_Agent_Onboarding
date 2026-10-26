"""No model calls: validate opt-in rehearsal installation and HTTP evidence gates."""
import shutil
import subprocess
from urllib.request import urlopen

import pytest

import coding_rehearsal as rehearsal

TEMPLATE = rehearsal.ROOT / ".github/skills/perf-setup/template"


def test_existing_entry_installs_only_agent_files_and_preserves_dirty_work(tmp_path):
    checkout = tmp_path / "existing"
    shutil.copytree(TEMPLATE, checkout, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    subprocess.run(["git", "init", "-q", str(checkout)], check=True)
    dirty = checkout / "src/test/resources/dirty.csv"
    dirty.write_text("local-dummy-existing-work\n")
    report = rehearsal.install_in_fixture(checkout)
    assert report["protected_files_unchanged"] > 20
    assert len(report["added"]) == 12
    assert dirty.read_text() == "local-dummy-existing-work\n"
    assert (checkout / ".github/agents/perf-coding.agent.md").is_file()


def test_fixture_install_normalizes_macos_style_checkout_alias(tmp_path):
    real = tmp_path / "real"
    shutil.copytree(TEMPLATE, real, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    subprocess.run(["git", "init", "-q", str(real)], check=True)
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    assert rehearsal.install_in_fixture(alias)["added"]


def test_orders_http_rehearsal_executes_the_generated_flow_and_cleans_up(tmp_path, monkeypatch):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        source = tmp_path / "src/test/kotlin/cz/example/perf/contract/AgentRehearsalSimulation.kt"
        text = source.read_text()
        assert "OrdersFlows.basicOrders()" in text
        assert "atOnceUsers(1)" in text and ".disableFollowRedirect()" in text
        target = next(value.split("=", 1)[1] for value in command if value.startswith("-DcontractBaseUrl="))
        with urlopen(target + "/orders", timeout=2) as response:
            assert response.status == 200
        return subprocess.CompletedProcess(command, 0, "Synthetic Maven result", "")

    monkeypatch.setattr(rehearsal, "run_maven", run)
    result = rehearsal.verify_http(tmp_path, "orders", tmp_path / "evidence")
    assert result["passed"]
    assert result["observed_requests"] == {"/orders": 1}
    assert not (tmp_path / "src/test/kotlin/cz/example/perf/contract/AgentRehearsalSimulation.kt").exists()
    assert (tmp_path / "evidence.http.json").is_file()
    assert calls


def test_successful_build_cannot_hide_missing_generated_flow_traffic(tmp_path, monkeypatch):
    monkeypatch.setattr(rehearsal, "run_maven",
                        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "", ""))
    result = rehearsal.verify_http(tmp_path, "orders")
    assert not result["passed"]
    assert result["observed_requests"] == {}


def test_http_failure_does_not_leave_the_harness_simulation(tmp_path, monkeypatch):
    def timeout(command, **kwargs):
        raise subprocess.TimeoutExpired(command, 240)

    monkeypatch.setattr(rehearsal, "run_maven", timeout)
    with pytest.raises(subprocess.TimeoutExpired):
        rehearsal.verify_http(tmp_path, "orders", tmp_path / "timeout")
    assert not (tmp_path / "src/test/kotlin/cz/example/perf/contract/AgentRehearsalSimulation.kt").exists()
    report = rehearsal.json.loads((tmp_path / "timeout.http.json").read_text())
    assert not report["passed"]
    assert "execution_error" in report


def test_items_contract_uses_generated_dummy_ids_and_both_real_flows(tmp_path, monkeypatch):
    csv = tmp_path / "src/test/resources/items/items.csv"
    csv.parent.mkdir(parents=True)
    csv.write_text("itemId,token\nlocal-dummy-1,local-dummy-token\n")

    def run(command, **kwargs):
        source = tmp_path / "src/test/kotlin/cz/example/perf/contract/AgentRehearsalSimulation.kt"
        assert "ItemsFlows.browseItems()" in source.read_text()
        assert "ItemsFlows.viewItemDetails()" in source.read_text()
        target = next(value.split("=", 1)[1] for value in command if value.startswith("-DcontractBaseUrl="))
        for path in ("/items", "/items/local-dummy-1"):
            with urlopen(target + path, timeout=2) as response:
                assert response.status == 200
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(rehearsal, "run_maven", run)
    assert rehearsal.verify_http(tmp_path, "items")["passed"]
    csv.write_text("itemId\nnon-synthetic\n")
    with pytest.raises(ValueError, match="requires synthetic"):
        rehearsal.verify_http(tmp_path, "items")


def test_maven_timeout_stops_its_own_process_tree(tmp_path, monkeypatch):
    import run_scenarios

    class Process:
        def communicate(self, timeout):
            raise subprocess.TimeoutExpired("maven", timeout)

    process, stopped, launched = Process(), [], []

    def launch(command, **kwargs):
        launched.append(kwargs)
        return process

    monkeypatch.setattr(rehearsal.subprocess, "Popen", launch)
    monkeypatch.setattr(run_scenarios, "stop_process_tree", stopped.append)
    with pytest.raises(subprocess.TimeoutExpired):
        rehearsal.run_maven(["./mvnw"], cwd=tmp_path, timeout=1)
    assert stopped == [process]
    assert launched[0]["start_new_session"] == (rehearsal.os.name == "posix")

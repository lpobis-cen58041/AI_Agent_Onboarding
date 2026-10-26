"""Local readiness must not make remote or authentication checks."""
import importlib.util
import sys
from pathlib import Path


def test_local_only_skips_network_checks(monkeypatch):
    path = Path(__file__).resolve().parents[1] / ".github/scripts/check_env.py"
    spec = importlib.util.spec_from_file_location("check_env_local_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls = []
    monkeypatch.setattr(module, "check_java", lambda: calls.append("java"))
    monkeypatch.setattr(module, "check_tool", lambda *args: calls.append("git"))
    monkeypatch.setattr(module, "check_ide", lambda: calls.append("ide"))
    def unexpected(*args):
        raise AssertionError("Local readiness must not contact remote systems")
    monkeypatch.setattr(module, "check_github", unexpected)
    monkeypatch.setattr(module, "check_http", unexpected)
    monkeypatch.setattr(sys, "argv", ["check_env.py", "--local-only"])
    module.main()
    assert calls == ["java", "git", "ide"]

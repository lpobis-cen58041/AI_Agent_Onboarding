"""Validate launcher permissions and process arguments without model calls."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github/skills/perf-setup/template/.github/scripts/start_coding.py"
spec = importlib.util.spec_from_file_location("start_coding", SCRIPT)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


@pytest.mark.parametrize("options,tail", [
    ([], ["-i", "Start"]),
    (["--prompt", "A request; not a shell command"], ["-i", "A request; not a shell command"]),
    (["--resume"], ["--resume"]),
    (["--resume", "exact-session"], ["--resume", "exact-session"]),
])
def test_launch_uses_only_helper_permissions_and_preserves_exit_status(monkeypatch, options, tail):
    calls = []
    monkeypatch.setattr(sys, "argv", ["start_coding.py", *options])
    monkeypatch.setattr(launcher.shutil, "which", lambda name: "/tools/copilot")

    def call(command, **kwargs):
        calls.append((command, kwargs))
        return 7

    monkeypatch.setattr(launcher.subprocess, "call", call)
    assert launcher.main() == 7
    command, kwargs = calls[0]
    assert command == ["/tools/copilot", "--agent", "perf-coding", "--model", "gpt-6-astra",
                       "--allow-tool=shell(python .github/scripts/task_state.py:*)",
                       "--allow-tool=shell(python .github/scripts/new_domain.py:*)",
                       "--allow-tool=shell(python3 .github/scripts/task_state.py:*)",
                       "--allow-tool=shell(python3 .github/scripts/new_domain.py:*)", *tail]
    assert kwargs == {"cwd": SCRIPT.parents[2]}


def test_missing_cli_is_an_explicit_error(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["start_coding.py"])
    monkeypatch.setattr(launcher.shutil, "which", lambda name: None)
    assert launcher.main() == 1
    assert "not installed or not on PATH" in capsys.readouterr().err


def test_prompt_and_resume_cannot_be_combined(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["start_coding.py", "--resume", "--prompt", "Start"])
    with pytest.raises(SystemExit, match="2"):
        launcher.main()


def test_launch_failure_is_visible(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["start_coding.py"])
    monkeypatch.setattr(launcher.shutil, "which", lambda name: "/tools/copilot")

    def fail(*args, **kwargs):
        raise OSError("cannot execute")

    monkeypatch.setattr(launcher.subprocess, "call", fail)
    assert launcher.main() == 1
    assert "cannot launch Copilot" in capsys.readouterr().err


def test_fresh_scaffold_launcher_runs_from_another_directory(tmp_path):
    scaffold = ROOT / ".github/scripts/scaffold.py"
    subprocess.run([sys.executable, str(scaffold), "launcher-test", "--dest", str(tmp_path),
                    "--no-test", "--no-git"], check=True, capture_output=True)
    script = tmp_path / "launcher-test/.github/scripts/start_coding.py"
    result = subprocess.run([sys.executable, str(script), "--help"], cwd=tmp_path,
                            capture_output=True, text=True, check=True)
    assert "--resume" in result.stdout
    assert "--prompt" in result.stdout
    binary = tmp_path / "bin"
    binary.mkdir()
    fake = binary / "copilot"
    fake.write_text(
        f"#!{sys.executable}\n"
        "import json,os,sys\n"
        "print(json.dumps({'cwd':os.getcwd(),'args':sys.argv[1:]}))\n"
    )
    fake.chmod(0o755)
    result = subprocess.run([sys.executable, str(script)], cwd=tmp_path,
                            env={**os.environ, "PATH": str(binary)}, capture_output=True, text=True,
                            check=True)
    captured = json.loads(result.stdout.splitlines()[-1])
    assert Path(captured["cwd"]) == (tmp_path / "launcher-test").resolve()
    assert captured["args"][-2:] == ["-i", "Start"]
    assert len([arg for arg in captured["args"] if arg.startswith("--allow-tool=")]) == 4
    (script.parent / "new_domain.py").unlink()
    result = subprocess.run([sys.executable, str(script)], cwd=tmp_path,
                            env={**os.environ, "PATH": str(binary)}, capture_output=True, text=True)
    assert result.returncode == 1
    assert "missing repository helper: new_domain.py" in result.stderr

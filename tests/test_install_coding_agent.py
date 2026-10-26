"""Agent-only installation checks use local Git fixtures; no model, network or build."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github/scripts/install_coding_agent.py"
spec = importlib.util.spec_from_file_location("install_coding_agent", SCRIPT)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


@pytest.fixture
def checkout(tmp_path):
    root = tmp_path / "existing-project"
    shutil.copytree(installer.TEMPLATE, root, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for relative in installer.MANAGED:
        (root / relative).unlink()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def snapshot(root):
    return {str(path.relative_to(root)): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file() and not path.is_symlink() and ".git" not in path.relative_to(root).parts}


def test_preview_is_read_only_and_limits_exact_file_scope(checkout):
    original = snapshot(checkout)
    plan, _ = installer.preview(checkout)
    assert snapshot(checkout) == original
    assert plan["compatibility"] == "structurally-compatible", plan["blockers"]
    assert {item["action"] for item in plan["files"]} == {"add"}
    paths = {item["path"] for item in plan["files"]}
    assert paths == {*installer.MANAGED, installer.STATE_IGNORE}
    assert not any(path.startswith(("src/", "ci/")) for path in paths)
    assert ".github/scripts/check_items_http.py" not in paths


def test_clean_scaffold_supports_install_before_any_domain_exists(tmp_path):
    root = tmp_path / "clean"
    subprocess.run([sys.executable, str(ROOT / ".github/scripts/scaffold.py"), "clean",
                    "--dest", str(tmp_path), "--no-test", "--no-git"], check=True, capture_output=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for relative in installer.MANAGED:
        (root / relative).unlink()
    assert not (root / f"{installer.BASE}/domain").exists()
    original = snapshot(root)
    plan, _ = installer.preview(root)
    assert not plan["blockers"], plan["blockers"]
    installer.apply(root, plan["plan_sha256"])
    assert all(snapshot(root)[name] == content for name, content in original.items())
    generated = subprocess.run([sys.executable, ".github/scripts/new_domain.py", ".", "orders", "--dry-run"],
                               cwd=root, capture_output=True, text=True)
    assert generated.returncode == 0, generated.stderr
    assert not (root / f"{installer.BASE}/domain").exists()


def test_legacy_weight_sum_test_is_still_supported(checkout):
    (checkout / "src/test/kotlin/cz/example/perf/setup/MixBuilderTest.kt").unlink()
    plan, _ = installer.preview(checkout)
    assert not plan["blockers"]


def test_invalid_env_content_is_not_mistaken_for_an_empty_project(checkout):
    for env in ("test", "prod"):
        (checkout / f"src/main/resources/env/{env}.properties").write_text("not properties\n")
    plan, _ = installer.preview(checkout)
    assert any("expected key=value" in error for error in plan["blockers"])


def test_approved_install_preserves_all_other_files_and_is_idempotent(checkout):
    subprocess.run(["git", "-C", str(checkout), "add", "-A"], check=True)
    index = (checkout / ".git/index").read_bytes()
    (checkout / "src/main/kotlin/custom.kt").write_text("// user work, uncommitted\n")
    (checkout / ".github/agents/team.agent.md").write_text("Team agent\n")
    original = snapshot(checkout)
    plan, contents = installer.preview(checkout)
    _, added = installer.apply(checkout, plan["plan_sha256"])
    assert len(added) == len(installer.MANAGED) + 1
    after = snapshot(checkout)
    assert all(after[path] == content for path, content in original.items())
    assert all(after[path] == content for path, content in contents.items())
    plan, _ = installer.preview(checkout)
    assert not plan["blockers"]
    assert all(item["action"] == "unchanged" for item in plan["files"])
    assert installer.apply(checkout, plan["plan_sha256"])[1] == []
    assert snapshot(checkout) == after
    assert (checkout / ".git/index").read_bytes() == index
    ignored = subprocess.run(
        ["git", "-C", str(checkout), "check-ignore", ".perf-coding/tasks/example.json"],
        capture_output=True, text=True,
    )
    assert ignored.returncode == 0


@pytest.mark.parametrize("relative", [
    ".github/copilot-instructions.md", ".github/agents/perf-coding.agent.md",
    ".github/scripts/new_domain.py", ".perf-coding/.gitignore",
])
def test_conflicting_content_blocks_whole_install_without_overwrites(checkout, relative):
    path = checkout / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("Existing project content\n")
    original = snapshot(checkout)
    plan, _ = installer.preview(checkout)
    assert any(item["path"] == relative and item["action"] == "conflict" for item in plan["files"])
    with pytest.raises(ValueError, match="Installation blocked"):
        installer.apply(checkout, plan["plan_sha256"])
    assert snapshot(checkout) == original


@pytest.mark.parametrize("relative", [
    "pom.xml", f"{installer.BASE}/config/Protocols.kt",
    f"{installer.BASE}/setup/MixBuilder.kt", "src/main/resources/env/prod.properties",
])
def test_incompatible_project_is_not_adapted_automatically(checkout, relative):
    (checkout / relative).write_text("Different project\n")
    before = snapshot(checkout)
    plan, _ = installer.preview(checkout)
    assert plan["blockers"]
    with pytest.raises(ValueError, match="Installation blocked"):
        installer.apply(checkout, plan["plan_sha256"])
    assert snapshot(checkout) == before


def test_old_target_rps_only_config_is_not_migrated_by_install(checkout):
    path = checkout / f"{installer.BASE}/config/Config.kt"
    path.write_text(
        "package cz.example.perf.config\n"
        "object Config { val baseUrl = \"http://localhost:8080\"; val apiKey = \"dummy\";"
        "val targetRps = 2.0 }\n"
    )
    before = snapshot(checkout)
    plan, _ = installer.preview(checkout)
    assert not plan["blockers"]
    installer.apply(checkout, plan["plan_sha256"])
    assert all(snapshot(checkout)[name] == content for name, content in before.items())


@pytest.mark.parametrize("relative", [
    ".github/agents", ".github/skills/perf-coding", ".perf-coding",
    f"{installer.BASE}/config/Config.kt",
])
def test_symlinks_block_install_without_touching_outside_files(checkout, tmp_path, relative):
    path = checkout / relative
    outside = tmp_path / "outside"
    if path.is_dir():
        shutil.rmtree(path)
        outside.mkdir()
        path.symlink_to(outside, target_is_directory=True)
    elif path.is_file():
        path.unlink()
        outside.write_text("Keep outside file\n")
        path.symlink_to(outside)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        outside.mkdir()
        path.symlink_to(outside, target_is_directory=True)
    plan, _ = installer.preview(checkout)
    assert plan["blockers"]
    with pytest.raises(ValueError, match="Installation blocked"):
        installer.apply(checkout, plan["plan_sha256"])
    if outside.is_file():
        assert outside.read_text() == "Keep outside file\n"
    else:
        assert not list(outside.iterdir())


def test_approval_binds_target_inputs_and_install_sources(checkout, monkeypatch):
    plan, _ = installer.preview(checkout)
    path = checkout / f"{installer.BASE}/config/Config.kt"
    path.write_text(path.read_text() + "\n// changed after preview\n")
    with pytest.raises(ValueError, match="Preview changed"):
        installer.apply(checkout, plan["plan_sha256"])
    fresh, _ = installer.preview(checkout)
    original = installer.payloads

    def changed(name):
        payload = original(name)
        payload[".github/agents/perf-coding.agent.md"] += b"\nUpdated installer source\n"
        return payload

    monkeypatch.setattr(installer, "payloads", changed)
    with pytest.raises(ValueError, match="Preview changed"):
        installer.apply(checkout, fresh["plan_sha256"])
    assert not (checkout / ".github/agents/perf-coding.agent.md").exists()


def test_partial_install_rolls_back_only_new_files(checkout, monkeypatch):
    plan, _ = installer.preview(checkout)
    before = snapshot(checkout)
    original = Path.open
    writes = []

    def fail_second_write(path, mode="r", *args, **kwargs):
        if mode == "xb":
            writes.append(path)
            if len(writes) == 2:
                raise PermissionError("synthetic write failure")
        return original(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_second_write)
    with pytest.raises(ValueError, match="Installation failed"):
        installer.apply(checkout, plan["plan_sha256"])
    assert snapshot(checkout) == before


def test_non_checkout_and_checkout_subdirectory_are_rejected(checkout, tmp_path):
    for path in (tmp_path, checkout / "src"):
        with pytest.raises(ValueError, match="root of an existing"):
            installer.preview(path)


def test_cli_requires_exact_explicit_approval(checkout):
    command = [sys.executable, str(SCRIPT), str(checkout)]
    preview = subprocess.run(command, capture_output=True, text=True, check=True)
    plan = json.loads(preview.stdout)
    bad = subprocess.run(command + ["--apply", "not-approved"], capture_output=True, text=True)
    assert bad.returncode != 0 and "approval hash" in bad.stderr
    result = subprocess.run(command + ["--apply", plan["plan_sha256"]],
                            capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)["added"]


def test_state_ignore_is_local_and_does_not_rewrite_root_ignore(checkout):
    ignore = checkout / ".gitignore"
    ignore.write_text("target/\n.env\n")
    plan, _ = installer.preview(checkout)
    installer.apply(checkout, plan["plan_sha256"])
    assert ignore.read_text() == "target/\n.env\n"
    result = subprocess.run(
        ["git", "-C", str(checkout), "check-ignore", ".perf-coding/tasks/example.json"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0


def test_parent_regular_file_is_a_preview_conflict(checkout):
    path = checkout / ".github/agents"
    path.rmdir()
    path.write_text("Not a directory\n")
    plan, _ = installer.preview(checkout)
    assert any("Parent is not a directory" in blocker for blocker in plan["blockers"])


def test_installer_never_reads_env_secret_file(checkout, monkeypatch):
    path = checkout / ".env"
    path.write_text("synthetic sensitive fixture; do not read\n")
    original = Path.open

    def guarded(path, *args, **kwargs):
        assert path.name != ".env", "installer must not read .env"
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded)
    plan, _ = installer.preview(checkout)
    installer.apply(checkout, plan["plan_sha256"])


def test_onboarding_distinguishes_requested_install_from_existing_workflow():
    playbook = (ROOT / ".github/skills/perf-setup/playbooks/repo.md").read_text()
    for requirement in ("install_coding_agent.py", "--apply <plan_sha256>",
                        "Ask the user to approve", "Incompatible", "independent review"):
        assert requirement.lower() in playbook.lower()
    scenarios = {item["id"]: item for item in json.loads((ROOT / "tests/scenarios.json").read_text())}
    assert "own workflow" in scenarios["existing-repository-without-coding-agent"]["prompt"]
    assert "do not execute commands or edit files" in scenarios["existing-repository-agent-install-preview"]["prompt"]

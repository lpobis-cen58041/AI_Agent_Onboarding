"""Preview an agent-only installation into an existing template-compatible Git checkout.

Preview: python install_coding_agent.py /path/to/checkout
Apply:   python install_coding_agent.py /path/to/checkout --apply <preview-plan-sha256>

No clone, network, build, Git staging, overwrite or automatic adaptation is performed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

TEMPLATE = Path(__file__).resolve().parents[1] / "skills/perf-setup/template"
BASE = "src/main/kotlin/cz/example/perf"
MANAGED = (
    ".github/agents/perf-coding.agent.md",
    ".github/copilot-instructions.md",
    ".github/scripts/task_state.py",
    ".github/scripts/new_domain.py",
    ".github/skills/perf-coding/rules.md",
    ".github/skills/perf-coding/coding-guide.md",
    ".github/skills/perf-coding/endpoint-contracts.md",
    ".github/skills/perf-coding/task-state.md",
    ".github/skills/perf-coding/run-readiness.md",
    ".github/skills/perf-coding/playbooks/coder.md",
    ".github/skills/perf-coding/playbooks/reviewer.md",
)
STATE_IGNORE = ".perf-coding/.gitignore"
NS = {"m": "http://maven.apache.org/POM/4.0.0"}


def sha(content):
    return hashlib.sha256(content).hexdigest()


def literal_file(root, relative):
    """Reject symlinks and non-files without following paths outside the checkout."""
    path = root
    parts = Path(relative).parts
    for index, part in enumerate(parts):
        path /= part
        if path.is_symlink():
            raise ValueError(f"Symlink is unsupported: {relative}")
        if index < len(parts) - 1 and path.exists() and not path.is_dir():
            raise ValueError(f"Parent is not a directory: {relative}")
    if path.exists() and not path.is_file():
        raise ValueError(f"Expected a regular file: {relative}")
    return path


def git_root(root):
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                            capture_output=True, text=True, timeout=10)
    if result.returncode != 0 or Path(result.stdout.strip()).resolve() != root:
        raise ValueError("Pass the root of an existing, non-bare Git checkout (not a subdirectory).")


def payloads(project_name):
    result = {}
    for relative in MANAGED:
        content = (TEMPLATE / relative).read_text(encoding="utf-8")
        result[relative] = content.replace("__PROJECT_NAME__", project_name).encode("utf-8")
    # Ignore task records without modifying the repository's existing root .gitignore.
    result[STATE_IGNORE] = b"*\n!.gitignore\n"
    return result


def compatibility(root):
    """Conservative structural/API check; not proof that the build or API is correct."""
    blockers, inputs = [], {}

    def read(relative):
        try:
            path = literal_file(root, relative)
            content = path.read_bytes()
            inputs[relative] = sha(content)
            return content.decode("utf-8")
        except (ValueError, OSError, UnicodeError) as exc:
            blockers.append(f"{relative}: {exc}")
            return ""

    pom_text = read("pom.xml")
    project_name = root.name
    try:
        pom = ET.fromstring(pom_text)
        project_name = pom.findtext("m:artifactId", namespaces=NS) or project_name
        dependencies = {element.findtext("m:artifactId", namespaces=NS)
                        for element in pom.findall("m:dependencies/m:dependency", NS)}
        plugins = {element.findtext("m:artifactId", namespaces=NS)
                   for element in pom.findall("m:build/m:plugins/m:plugin", NS)}
        for artifact in ("gatling-core-java", "gatling-http-java", "kotlin-test-junit5"):
            if artifact not in dependencies:
                blockers.append(f"pom.xml: missing direct dependency {artifact}")
        for plugin in ("kotlin-maven-plugin", "gatling-maven-plugin", "detekt-maven-plugin"):
            if plugin not in plugins:
                blockers.append(f"pom.xml: missing build plugin {plugin}")
    except ET.ParseError as exc:
        blockers.append(f"pom.xml: invalid Maven XML: {exc}")

    contracts = {
        f"{BASE}/config/Config.kt": ("object Config", "baseUrl", "apiKey"),
        f"{BASE}/config/Env.kt": ("object Env", "operator fun get"),
        f"{BASE}/config/Protocols.kt": ("object Protocols", "val api"),
        f"{BASE}/auth/Auth.kt": ("object Auth", "fun withTokenFromSession("),
        f"{BASE}/setup/UseCase.kt": ("UseCase", "name", "defaultWeight", "chain"),
        f"{BASE}/setup/MixBuilder.kt": ("MixBuilder", "fun fromDefaults("),
        f"{BASE}/setup/SimulationSetup.kt": ("SimulationSetup", "fun run("),
        "src/test/kotlin/cz/example/perf/testutil/GatlingTestBootstrap.kt":
            ("object GatlingTestBootstrap", "fun init("),
    }
    for relative, tokens in contracts.items():
        text = read(relative)
        expected_package = relative.rsplit("/", 1)[0].split("/kotlin/")[1].replace("/", ".")
        if f"package {expected_package}" not in text or any(token not in text for token in tokens):
            blockers.append(f"{relative}: unsupported package/API; adapt instructions manually")
    test_base = "src/test/kotlin/cz/example/perf/setup"
    mix_tests = ("MixBuilderTest", "WeightSumTest")
    found_test = False
    for name in mix_tests:
        relative = f"{test_base}/{name}.kt"
        if (root / relative).exists() or (root / relative).is_symlink():
            text = read(relative)
            found_test = True
            if "package cz.example.perf.setup" not in text or f"class {name}" not in text:
                blockers.append(f"{relative}: unsupported package/API; adapt instructions manually")
    if not found_test:
        blockers.append(f"{test_base}: expected MixBuilderTest.kt or legacy WeightSumTest.kt")
    for relative in ("mvnw", ".mvn/wrapper/maven-wrapper.properties", "detekt.yml"):
        read(relative)
    if (root / "mvnw").exists() and not os.access(root / "mvnw", os.X_OK):
        blockers.append("mvnw is not executable; confirm and fix repository prerequisites first")
    env_keys = []
    for env in ("test", "prod"):
        text = read(f"src/main/resources/env/{env}.properties")
        entries = [line for line in text.splitlines()
                   if line.strip() and not line.lstrip().startswith(("#", "!"))]
        if any("=" not in line or not line.split("=", 1)[0].strip() for line in entries):
            blockers.append(f"env/{env}.properties: expected key=value entries or comments")
        keys = {line.split("=", 1)[0].strip() for line in entries if "=" in line}
        env_keys.append(keys)
    if env_keys[0] != env_keys[1]:
        blockers.append("env/test.properties and env/prod.properties must declare matching keys")
    ci_lines = read("ci/simulation-data.csv").splitlines()
    if not ci_lines or ci_lines[0] != "simulation,source,target":
        blockers.append("ci/simulation-data.csv: unsupported header")
    for relative in (f"{BASE}/domain", f"{BASE}/simulations/domain"):
        path = root
        for part in Path(relative).parts:
            path /= part
            if path.is_symlink():
                blockers.append(f"{relative}: symlink directory is unsupported")
                break
            if path.exists() and not path.is_dir():
                blockers.append(f"{relative}: expected a directory")
                break
    return project_name, inputs, blockers


def preview(root):
    git_root(root)
    project_name, inputs, blockers = compatibility(root)
    files = []
    contents = payloads(project_name)
    for relative, content in contents.items():
        current = None
        try:
            path = literal_file(root, relative)
            current = path.read_bytes() if path.exists() else None
            action = "add" if current is None else "unchanged" if current == content else "conflict"
        except (ValueError, OSError) as exc:
            action = "conflict"
            blockers.append(f"{relative}: {exc}")
        if action == "conflict":
            blockers.append(f"{relative}: installation would overwrite existing content; reconcile manually")
        files.append({"path": relative, "action": action, "sha256": sha(content),
                      "existing_sha256": sha(current) if current is not None else None})
    plan = {
        "repository": str(root), "project": project_name,
        "compatibility": "blocked" if blockers else "structurally-compatible",
        "files": files, "blockers": blockers,
        "checked_inputs": inputs,
        "limits": [
            "Static compatibility only: no build, tool/model availability or live API verified.",
            "Only the listed agent instructions/helpers and task-state ignore file are installed.",
            "Existing differing files are never overwritten; no upgrades or automatic merges.",
            "Existing application code, tests, build, root ignore file and CI are not changed.",
        ],
    }
    plan["plan_sha256"] = sha(json.dumps(plan, sort_keys=True).encode())
    return plan, contents


def apply(root, approved):
    plan, contents = preview(root)
    if plan["blockers"]:
        raise ValueError("Installation blocked:\n" + "\n".join(plan["blockers"]))
    if approved != plan["plan_sha256"]:
        raise ValueError("Preview changed or approval hash is invalid. Review a fresh preview before applying.")
    created_files, created_dirs = [], []
    try:
        for item in plan["files"]:
            if item["action"] == "unchanged":
                continue
            path = literal_file(root, item["path"])
            missing_dirs = []
            parent = path.parent
            while not parent.exists():
                missing_dirs.append(parent)
                parent = parent.parent
            for directory in reversed(missing_dirs):
                directory.mkdir()
                created_dirs.append(directory)
            with path.open("xb") as stream:
                created_files.append((path, contents[item["path"]]))
                stream.write(contents[item["path"]])
    except OSError as exc:
        cleanup_errors = []
        for path, content in reversed(created_files):
            try:
                # Never delete a file concurrently replaced/modified by someone else.
                if path.is_symlink() or path.read_bytes() != content:
                    cleanup_errors.append(f"Preserved changed/partial file: {path}")
                else:
                    path.unlink()
            except OSError as cleanup:
                cleanup_errors.append(str(cleanup))
        for directory in reversed(created_dirs):
            try:
                directory.rmdir()
            except OSError as cleanup:
                cleanup_errors.append(str(cleanup))
        raise ValueError(f"Installation failed: {exc}\n" + "\n".join(cleanup_errors)) from exc
    return plan, [str(path.relative_to(root)) for path, _ in created_files]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    parser.add_argument("--apply", metavar="PLAN_SHA256",
                        help="explicitly approve the exact preview; default is read-only")
    args = parser.parse_args()
    root = args.repository.expanduser().resolve()
    try:
        if args.apply:
            plan, added = apply(root, args.apply)
            print(json.dumps({"repository": str(root), "added": added,
                              "unchanged": [item["path"] for item in plan["files"]
                                            if item["action"] == "unchanged"]}, indent=2))
        else:
            plan, _ = preview(root)
            print(json.dumps(plan, indent=2))
            return 1 if plan["blockers"] else 0
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

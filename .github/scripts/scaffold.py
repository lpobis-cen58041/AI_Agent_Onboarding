"""Create a local perf-test repo with shared infrastructure only (no remote is created).

  python scaffold.py my-perf-project [--demo] [--dest ~/dev] [--runner ubuntu-latest] [--no-test] [--no-git | --no-commit]

Copies shared template files to <dest>/<name>; --demo also includes the items example and mock suite.
Replaces placeholders, runs `./mvnw -q test` (unless --no-test) and initializes Git with a first commit
(unless --no-git; --no-commit initializes Git without staging or committing).
"""
import argparse
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / "skills" / "perf-setup" / "template"
TEXT_EXT = {".xml", ".md", ".yml", ".kt", ".csv", ".properties", ".gitignore"}
DEMO_ONLY = {
    "src/main/kotlin/cz/example/perf/domain",
    "src/main/kotlin/cz/example/perf/simulations/domain",
    "src/test/kotlin/cz/example/perf/domain",
    "src/test/kotlin/cz/example/perf/contract",
    "src/test/kotlin/cz/example/perf/setup/WeightSumTest.kt",
    "src/test/resources/items",
    ".github/scripts/check_items_http.py",
    ".github/workflows/DemoHttp.yml",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--dest", type=Path, default=Path.home() / "dev")
    ap.add_argument("--runner", default="ubuntu-latest", help="value for <RUNNER_LABEL> in the PR workflow")
    ap.add_argument("--demo", action="store_true", help="include the items sample domain and optional mock suite")
    ap.add_argument("--no-test", action="store_true")
    git = ap.add_mutually_exclusive_group()
    git.add_argument("--no-git", action="store_true")
    git.add_argument("--no-commit", action="store_true", help="run git init only; no staging or commit")
    a = ap.parse_args()

    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", a.name):
        print("ERROR: name must be lowercase letters, digits, '.', '_' or '-'.", file=sys.stderr)
        return 1
    target = a.dest.expanduser().resolve() / a.name
    if target.exists() or target.is_symlink():
        print(f"ERROR: {target} already exists.", file=sys.stderr)
        return 1

    def ignore(directory, names):
        ignored = set(shutil.ignore_patterns(
            ".perf-coding", "__pycache__", "*.pyc", "target", ".git", ".idea", "*.iml", ".env"
        )(directory, names))
        if not a.demo:
            relative = Path(directory).relative_to(TEMPLATE)
            ignored.update(name for name in names if (relative / name).as_posix() in DEMO_ONLY)
        return ignored

    shutil.copytree(TEMPLATE, target, ignore=ignore)
    if not a.demo:
        for env in ("test", "prod"):
            (target / f"src/main/resources/env/{env}.properties").write_text(
                "# Endpoint paths. Keep identical key sets in test.properties and prod.properties.\n"
                "# Empty until the first domain is added.\n", encoding="utf-8")
        (target / "ci/simulation-data.csv").write_text("simulation,source,target\n", encoding="utf-8")
    for f in target.rglob("*"):
        if f.is_file() and (f.suffix in TEXT_EXT or f.name == ".gitignore"):
            t = f.read_text(encoding="utf-8")
            f.write_text(t.replace("__PROJECT_NAME__", a.name).replace("<RUNNER_LABEL>", a.runner),
                         encoding="utf-8")
    (target / "mvnw").chmod(0o755)
    print(f"Created {target} ({'demo with items' if a.demo else 'new project; no domains'})")

    if not a.no_test:
        print("Running ./mvnw -q test ...")
        if subprocess.run(["./mvnw", "-q", "test"], cwd=target).returncode != 0:
            print("ERROR: build/test failed (repo left in place for inspection).", file=sys.stderr)
            return 1
        print("Build and tests OK.")
    if not a.no_git:
        run = lambda *c: subprocess.run(["git", *c], cwd=target, check=True, capture_output=True)
        run("init", "-q")
        if a.no_commit:
            print("Initialized empty git repository (no files staged or committed).")
        else:
            run("add", "-A")
            run("commit", "-q", "-m", "Initial commit from perf-setup template")
            print("Initialized git repository with first commit.")
    print(f'\nNext: cd {shlex.quote(str(target))} && copilot --agent perf-coding --model gpt-6-astra -i "Start"')
    print("The coding agent starts by asking about a new or existing domain.")
    print("Optional helper approvals: python3 .github/scripts/start_coding.py (from the new repo).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

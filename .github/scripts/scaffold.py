"""Create a local sample perf-test repo from the template (no remote is created).

  python scaffold.py my-perf-sample [--dest ~/dev] [--runner ubuntu-latest] [--no-test] [--no-git]

Copies .github/skills/perf-setup/template/ to <dest>/<name>, replaces placeholders,
runs `./mvnw -q test` (unless --no-test) and `git init` + first commit (unless --no-git).
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / "skills" / "perf-setup" / "template"
TEXT_EXT = {".xml", ".md", ".yml", ".kt", ".csv", ".properties", ".gitignore"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--dest", type=Path, default=Path.home() / "dev")
    ap.add_argument("--runner", default="ubuntu-latest", help="value for <RUNNER_LABEL> in the PR workflow")
    ap.add_argument("--no-test", action="store_true")
    ap.add_argument("--no-git", action="store_true")
    a = ap.parse_args()

    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", a.name):
        print("ERROR: name must be lowercase letters, digits, '.', '_' or '-'.", file=sys.stderr)
        return 1
    target = (a.dest.expanduser() / a.name).resolve()
    if target.exists():
        print(f"ERROR: {target} already exists.", file=sys.stderr)
        return 1

    shutil.copytree(TEMPLATE, target)
    for f in target.rglob("*"):
        if f.is_file() and (f.suffix in TEXT_EXT or f.name == ".gitignore"):
            t = f.read_text(encoding="utf-8")
            f.write_text(t.replace("__PROJECT_NAME__", a.name).replace("<RUNNER_LABEL>", a.runner),
                         encoding="utf-8")
    (target / "mvnw").chmod(0o755)
    print(f"Created {target}")

    if not a.no_test:
        print("Running ./mvnw -q test ...")
        if subprocess.run(["./mvnw", "-q", "test"], cwd=target).returncode != 0:
            print("ERROR: build/test failed (repo left in place for inspection).", file=sys.stderr)
            return 1
        print("Build and tests OK.")
    if not a.no_git:
        run = lambda *c: subprocess.run(["git", *c], cwd=target, check=True, capture_output=True)
        run("init", "-q")
        run("add", "-A")
        run("commit", "-q", "-m", "Initial commit from perf-setup template")
        print("Initialized git repository with first commit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

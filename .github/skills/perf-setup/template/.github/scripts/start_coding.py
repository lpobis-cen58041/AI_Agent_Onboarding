"""Launch the coding interview with session-scoped approvals for two local helpers."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--prompt", default="Start", help="first message for a new interview")
    choice.add_argument("--resume", nargs="?", const="", metavar="SESSION_ID",
                        help="resume a session by ID, or open the session picker")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    cli = shutil.which("copilot")
    if cli is None:
        print("ERROR: copilot CLI is not installed or not on PATH.", file=sys.stderr)
        return 1
    for name in ("task_state.py", "new_domain.py"):
        if not (root / ".github/scripts" / name).is_file():
            print(f"ERROR: missing repository helper: {name}", file=sys.stderr)
            return 1
    command = [cli, "--agent", "perf-coding", "--model", "gpt-6-astra"]
    for interpreter in ("python", "python3"):
        for name in ("task_state.py", "new_domain.py"):
            command.append(f"--allow-tool=shell({interpreter} .github/scripts/{name}:*)")
    if args.resume is None:
        command += ["-i", args.prompt]
    else:
        command.append("--resume")
        if args.resume:
            command.append(args.resume)
    print("Approving task_state.py and new_domain.py command prefixes for this session only.\n"
          "Other permissions remain subject to your existing CLI settings.", flush=True)
    try:
        return subprocess.call(command, cwd=root)
    except OSError as error:
        print(f"ERROR: cannot launch Copilot: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Check whether the current user appears to be in the required Redim/AD groups.

Sources of group info (first that works):
  - Windows: `whoami /groups`
  - macOS/Linux: `id -Gn` (only shows AD groups on domain-joined/bound machines)
Groups not found are reported as UNVERIFIED (not necessarily missing) - confirm in
the Windows request / ServiceNow. Exit 0 = all found, 2 = some not verified.

  python check_access.py [--env prod|test|all]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[1] / "skills" / "perf-setup" / "access.json"


def current_groups() -> set[str]:
    cmds = [["whoami", "/groups", "/fo", "csv", "/nh"]] if sys.platform == "win32" else [["id", "-Gn"]]
    out = ""
    for c in cmds:
        try:
            out = subprocess.run(c, capture_output=True, text=True, timeout=30).stdout
        except (OSError, subprocess.SubprocessError):
            pass
    tokens = out.replace('"', " ").replace(",", " ").split()
    return {t.upper().replace("/", "\\") for t in tokens}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default="all", choices=["prod", "test", "all"])
    a = ap.parse_args()
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    have = current_groups()
    missing = 0
    for env, groups in cfg["groups"].items():
        if a.env not in ("all", env):
            continue
        print(f"[{env}]  request rights in REDiM: {cfg.get('portals', {}).get(env, '?')}")
        for g in groups:
            ok = g.upper() in have or g.upper().split("\\")[-1] in have
            print(f"  {'OK        ' if ok else 'UNVERIFIED'} {g}")
            missing += not ok
    if missing:
        print(f"\n{missing} group(s) not verifiable from this machine (a Mac usually cannot list AD groups).")
        print("Confirm your request status in REDiM (links above), or run this on a Windows workstation.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

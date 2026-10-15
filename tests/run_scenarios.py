"""Run conversation scenarios against the perf-orchestrator agent with Copilot CLI (needs a logged-in `copilot`).

  python tests/run_scenarios.py [--only ID ...] [--runs N] [--model MODEL] [-j 4]

The agent runs read-only (tools: view, glob, grep), so it cannot execute scripts, change files or
submit anything. Each scenario passes when ALL `must` regexes match and NO `must_not` regex matches
(case-insensitive). With --runs N a scenario passes only if every run passes. Model output varies;
a failure is a prompt to read the answer (printed with -v), not always a bug.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = Path(__file__).with_name("scenarios.json")


def ask(prompt: str, model: str | None) -> str:
    cmd = ["copilot", "--agent", "perf-orchestrator", "-p", prompt, "--available-tools", "view", "glob", "grep", "task",
           "--no-ask-user", "--silent", "--allow-all-paths"]
    if model:
        cmd += ["--model", model]
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=400)
    if p.returncode != 0:
        raise RuntimeError(f"copilot exited {p.returncode}: {p.stderr[-300:]}")
    return p.stdout


def evaluate(sc: dict, answer: str) -> list[str]:
    problems = []
    for pat in sc.get("must", []):
        if not re.search(pat, answer, re.I):
            problems.append(f"missing: /{pat}/")
    for pat in sc.get("must_not", []):
        m = re.search(pat, answer, re.I)
        if m:
            problems.append(f"forbidden: /{pat}/ matched '{m.group(0)[:60]}'")
    return problems


def run_one(sc: dict, runs: int, model: str | None):
    results = []
    for _ in range(runs):
        try:
            ans = ask(sc["prompt"], model)
            results.append((evaluate(sc, ans), ans))
        except Exception as exc:  # noqa: BLE001
            results.append(([f"error: {exc}"], ""))
    return sc["id"], results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--model")
    ap.add_argument("-j", type=int, default=4)
    ap.add_argument("-v", action="store_true", help="print answers of failed runs")
    a = ap.parse_args()
    if not shutil.which("copilot"):
        print("copilot CLI not found", file=sys.stderr)
        return 2
    scenarios = [s for s in json.loads(SCENARIOS.read_text(encoding="utf-8")) if not a.only or s["id"] in a.only]
    with ThreadPoolExecutor(max_workers=a.j) as ex:
        outcomes = list(ex.map(lambda s: run_one(s, a.runs, a.model), scenarios))
    failed = 0
    for sid, results in outcomes:
        bad = [r for r in results if r[0]]
        print(f"{'FAIL' if bad else 'PASS'}  {sid}  ({len(results) - len(bad)}/{len(results)} runs)")
        for problems, ans in bad:
            failed += 1
            for pr in problems:
                print(f"      - {pr}")
            if a.v and ans:
                print("      ---- answer ----\n" + "\n".join("      " + l for l in ans.splitlines()[:25]))
    print(f"\n{len(outcomes)} scenario(s), {sum(1 for _, r in outcomes if any(x[0] for x in r))} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

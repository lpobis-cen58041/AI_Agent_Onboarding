"""Run conversation scenarios against the perf-orchestrator agent with Copilot CLI (needs a logged-in `copilot`).

  python tests/run_scenarios.py [--only ID ...] [--runs N] [--model MODEL] [-j 4] [--slow]

By default the agent runs read-only (tools: view, glob, grep, task), so it cannot execute scripts,
change files or submit anything. Scenarios with "workdir": "scaffold" run the `perf-coding` agent with
all tools in a throw-away scaffolded repo (slow, opt-in with --slow; deleted afterwards). Each scenario passes when ALL `must` regexes match and NO `must_not` regex matches
(case-insensitive). With --runs N a scenario passes only if every run passes. Model output varies;
a failure is a prompt to read the answer (printed with -v), not always a bug.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = Path(__file__).with_name("scenarios.json")


def ask(sc: dict, model: str | None) -> dict:
    cmd = ["copilot", "--agent", sc.get("agent", "perf-orchestrator"), "-p", sc["prompt"], "--no-ask-user",
           "--allow-all-paths", "--output-format", "json"]
    scaffolded = sc.get("workdir") == "scaffold"
    cmd += ["--allow-all-tools"] if scaffolded else ["--available-tools", "view", "glob", "grep", "task"]
    if model:
        cmd += ["--model", model]
    with tempfile.TemporaryDirectory() as tmp:
        cwd = ROOT
        if scaffolded:
            subprocess.run([sys.executable, str(ROOT / ".github/scripts/scaffold.py"), "sample", "--dest", tmp,
                            "--no-test"], check=True, capture_output=True)
            cwd = Path(tmp) / "sample"
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=900)
        if p.returncode != 0:
            raise RuntimeError(f"copilot exited {p.returncode}: {p.stderr[-300:]}")
        tr = parse_trace(p.stdout)
        tr["files_missing"] = [f for f in (sc.get("trace") or {}).get("files_exist", []) if not (cwd / f).exists()]
        return tr


def parse_trace(stdout: str) -> dict:
    """Final answer, reads (view paths) and sub-agent task prompts from Copilot's JSONL event stream."""
    answer, reads, tasks = "", [], []
    for line in stdout.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        d = ev.get("data") or {}
        if ev.get("type") == "assistant.message" and d.get("content"):
            answer = d["content"]
        elif ev.get("type") == "tool.execution_start":
            args = d.get("arguments") or {}
            if d.get("toolName") == "view":
                reads.append(args.get("path", ""))
            elif d.get("toolName") == "task":
                tasks.append(args.get("prompt", ""))
    return {"answer": answer, "reads": reads, "tasks": tasks}


def evaluate_trace(sc: dict, tr: dict) -> list[str]:
    """Process checks: the orchestrator must build sub-agents from data and verify their work."""
    spec = sc.get("trace")
    if not spec:
        return []
    problems, tasks = [], tr["tasks"]
    if len(tasks) < spec.get("min_subagents", 1):
        problems.append(f"expected >= {spec.get('min_subagents', 1)} sub-agent(s), got {len(tasks)}")
    for rel in spec.get("reads", []):
        if not any(rel in r for r in tr["reads"]):
            problems.append(f"orchestrator never read {rel}")
    if spec.get("rules_in_task") and not any("Never read or print" in x for x in tasks):
        problems.append("rules.md content not embedded in any sub-agent task")
    if spec.get("rules_in_reviewer") and not any("VERDICT" in x and "Never read or print" in x for x in tasks):
        problems.append("the reviewer task does not carry rules.md")
    problems += [f"expected file missing: {f}" for f in tr.get("files_missing", [])]
    if spec.get("reviewer") and not any("VERDICT" in x for x in tasks):
        problems.append("no reviewer sub-agent was spawned (no task asks for a VERDICT)")
    return problems


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
            tr = ask(sc, model)
            results.append((evaluate(sc, tr["answer"]) + evaluate_trace(sc, tr), tr["answer"]))
        except Exception as exc:  # noqa: BLE001
            results.append(([f"error: {exc}"], ""))
    return sc["id"], results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--model")
    ap.add_argument("-j", type=int, default=4)
    ap.add_argument("--slow", action="store_true", help="include scenarios that run in a scaffolded repo with all tools")
    ap.add_argument("-v", action="store_true", help="print answers of failed runs")
    a = ap.parse_args()
    if not shutil.which("copilot"):
        print("copilot CLI not found", file=sys.stderr)
        return 2
    scenarios = [s for s in json.loads(SCENARIOS.read_text(encoding="utf-8")) if (a.only and s["id"] in a.only) or (not a.only and (a.slow or not s.get("slow")))]
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

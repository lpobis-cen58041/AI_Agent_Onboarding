"""Run onboarding and coding scenarios with Copilot CLI (needs a logged-in `copilot`).

  python tests/run_scenarios.py [--only ID ...] [--runs N] [--model MODEL] [-j 4] [--slow]
  python tests/run_scenarios.py --onboarding --list
  python tests/run_scenarios.py --onboarding -j 1 -v

By default the agent runs with read-only tools (view, glob, grep, task).
"workdir": "template" selects the coding template with the same tool restrictions.
The allowlist normally omits ask_user; these -p cases check autonomous text responses.
interactive_cli cases use a real -i pseudo-terminal interview (serial, POSIX only).
Single-turn interactive cases allow ask_user; resumed multi-turn cases use text questions.
--no-ask-user (autonomous, no questions) is reserved for scaffold execution cases.
Scenarios with "workdir": "scaffold" run the `perf-coding` agent with all tools in a throw-away
scaffolded repo (slow, opt-in with --slow or an explicit --only; deleted afterwards).
Artifact checks and optional Maven verification run before fixture cleanup.
--rehearsal additionally approves owned loopback HTTP checks of generated real flows.
Each scenario passes when ALL `must` regexes match and NO `must_not` regex matches
(case-insensitive). With --runs N a scenario passes only if every run passes. Model output varies;
a failure is a prompt to read the answer (printed with -v), not always a bug.
"""
import argparse
import json
import math
import os
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import uuid
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path
from threading import Event

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = Path(__file__).with_name("scenarios.json")
TEMPLATE = ROOT / ".github/skills/perf-setup/template"


def stop_process_tree(process: subprocess.Popen) -> None:
    if os.name != "posix":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       check=True, capture_output=True, timeout=10)
        process.wait(timeout=5)
        return
    def signal_group(sig):
        # The session/group belongs only to this invocation, not other Copilot sessions.
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            return
        except PermissionError:
            # Darwin reports EPERM when a terminated group contains only zombies.
            rows = subprocess.run(["ps", "-axo", "pgid=,stat="], check=True,
                                  capture_output=True, text=True, timeout=10).stdout.splitlines()
            groups = [row.split() for row in rows if row.strip()]
            if any(group == str(process.pid) and not state.startswith("Z") for group, state in groups):
                members = [state for group, state in groups if group == str(process.pid)]
                raise PermissionError(f"Cannot stop owned process group {process.pid}; "
                                      f"observed member states: {members}") from None

    signal_group(signal.SIGTERM)
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
    signal_group(signal.SIGKILL)
    process.wait(timeout=5)


def cli_stage(path: Path) -> str:
    with path.open("rb") as stream:
        stream.seek(0, os.SEEK_END)
        stream.seek(max(0, stream.tell() - 65536))
        lines = stream.read().decode("utf-8", errors="replace").splitlines()
    for line in reversed(lines):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        kind, data = event.get("type"), event.get("data") or {}
        if kind in {"model.call_start", "tool.execution_start", "agent.interrupted", "assistant.message"}:
            detail = data.get("activity") or data.get("toolName") or data.get("model") or ""
            phase = data.get("cancelPhase")
            return f"{kind} {detail}" + (f" ({phase})" if phase else "")
    return "starting CLI (no model/tool event reported)"


def run_copilot(cmd, *, cwd, timeout=900, output_prefix=None, cancel_event=None):
    """Files avoid pipe-inheritance hangs and retain streamed output on timeout."""
    with ExitStack() as resources:
        if output_prefix is None:
            tmp = resources.enter_context(tempfile.TemporaryDirectory())
            output_prefix = Path(tmp) / "copilot"
        stdout_path = Path(f"{output_prefix}.stdout.jsonl")
        stderr_path = Path(f"{output_prefix}.stderr.log")
        stdout = resources.enter_context(stdout_path.open("wb"))
        stderr = resources.enter_context(stderr_path.open("wb"))
        process = subprocess.Popen(cmd, cwd=cwd, stdin=subprocess.DEVNULL,
                                   stdout=stdout, stderr=stderr,
                                   start_new_session=os.name == "posix")
        started = time.monotonic()
        next_report = 30
        try:
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    raise InterruptedError("scenario run cancelled")
                remaining = timeout - (time.monotonic() - started)
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(cmd, timeout)
                try:
                    process.wait(timeout=min(1 if cancel_event is not None else 30, remaining))
                    break
                except subprocess.TimeoutExpired:
                    if time.monotonic() - started >= timeout:
                        raise
                    elapsed = time.monotonic() - started
                    if elapsed >= next_report:
                        print(f"WAIT  CLI pid={process.pid}, elapsed={elapsed:.0f}s; "
                              f"stage: {cli_stage(stdout_path)}; stream: {stdout_path}", flush=True)
                        next_report = elapsed + 30
        except (subprocess.TimeoutExpired, KeyboardInterrupt, InterruptedError) as exc:
            stop_process_tree(process)
            if isinstance(exc, KeyboardInterrupt):
                raise
            tail = stderr_path.read_text(encoding="utf-8", errors="replace")[-2000:]
            partial = stdout_path.read_text(encoding="utf-8", errors="replace")[-2000:]
            reason = f"timed out after {timeout}s" if isinstance(exc, subprocess.TimeoutExpired) else "cancelled"
            raise RuntimeError(
                f"Copilot CLI {reason}; launched process tree stopped. "
                f"Last stage: {cli_stage(stdout_path)}. "
                f"Partial output: {stdout_path}; stderr: {stderr_path}\n{tail}\n{partial}"
            ) from exc
        return subprocess.CompletedProcess(
            cmd, process.returncode,
            stdout_path.read_text(encoding="utf-8", errors="replace"),
            stderr_path.read_text(encoding="utf-8", errors="replace"),
        )


def run_interactive_copilot(cmd, *, cwd, timeout=900, output_prefix=None, cancel_event=None,
                            resume=False):
    """Exercise the actual -i interview; -p can suppress clarification even without --no-ask-user."""
    if os.name != "posix":
        raise ValueError("Interactive CLI regressions currently require a POSIX pseudo-terminal.")
    import fcntl
    import pty
    import select
    import struct
    import termios

    session_id = cmd[cmd.index("--session-id") + 1]
    events = Path.home() / ".copilot/session-state" / session_id / "events.jsonl"
    if events.exists() and not resume:
        raise ValueError("Interactive regression requires a fresh session ID.")
    if resume and not events.is_file():
        raise ValueError("Interactive resume requires the previous session's event file.")
    offset = events.stat().st_size if resume else 0
    prompt_index = cmd.index("-p")
    interactive = list(cmd)
    interactive[prompt_index] = "-i"
    output_index = interactive.index("--output-format")
    del interactive[output_index:output_index + 2]
    interactive += ["--no-color", "--allow-tool", "view", "--allow-tool", "glob", "--allow-tool", "grep"]
    with ExitStack() as resources:
        if output_prefix is None:
            tmp = resources.enter_context(tempfile.TemporaryDirectory())
            output_prefix = Path(tmp) / "interactive"
        stdout_path = Path(f"{output_prefix}.stdout.jsonl")
        screen_path = Path(f"{output_prefix}.terminal.log")
        screen = resources.enter_context(screen_path.open("wb"))
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 45, 140, 0, 0))
        try:
            process = subprocess.Popen(interactive, cwd=cwd, stdin=slave, stdout=slave, stderr=slave,
                                       start_new_session=True, env={**os.environ, "TERM": "xterm-256color"})
        except OSError:
            os.close(master)
            raise
        finally:
            os.close(slave)
        started, next_report, trusted = time.monotonic(), 30, False
        terminal_tail, finished = b"", False
        try:
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    raise RuntimeError("Interactive CLI regression cancelled")
                if time.monotonic() - started >= timeout:
                    raise RuntimeError(f"Interactive CLI timed out after {timeout}s; partial screen: {screen_path}")
                if select.select([master], [], [], 0.1)[0]:
                    try:
                        chunk = os.read(master, 65536)
                    except OSError:
                        chunk = b""
                    screen.write(chunk)
                    screen.flush()
                    terminal_tail = (terminal_tail + chunk)[-32768:]
                    # Approve only this known fixture's folder trust, never tool/edit/command dialogs.
                    if not trusted and b"Confirm folder trust" in terminal_tail:
                        os.write(master, b"\r")
                        trusted = True
                raw = interactive_events_since(events, offset)
                complete = []
                for line in raw.splitlines():
                    try:
                        complete.append(json.loads(line))
                    except ValueError:
                        continue
                question = any(
                    event.get("type") == "tool.execution_start"
                    and (event.get("data") or {}).get("toolName") == "ask_user"
                    for event in complete
                )
                finished = interactive_turn_finished(complete)
                if question or finished:
                    return subprocess.CompletedProcess(cmd, 0, raw, "")
                if process.poll() is not None:
                    return subprocess.CompletedProcess(cmd, process.returncode or 1, raw,
                                                       "Interactive CLI exited without an input request or completed turn.")
                elapsed = time.monotonic() - started
                if elapsed >= next_report:
                    print(f"WAIT  interactive CLI pid={process.pid}, elapsed={elapsed:.0f}s; "
                          f"screen: {screen_path}", flush=True)
                    next_report = elapsed + 30
        finally:
            try:
                if finished and process.poll() is None:
                    os.write(master, b"/exit\r")
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        stop_process_tree(process)
                else:
                    stop_process_tree(process)
            finally:
                os.close(master)
                if events.exists():
                    stdout_path.write_text(interactive_events_since(events, offset), encoding="utf-8")


def interactive_events_since(path, offset):
    """A resumed interview must never count an older answer/question as this turn's result."""
    if not path.exists():
        return ""
    with path.open("rb") as stream:
        stream.seek(offset)
        return stream.read().decode("utf-8", errors="replace")


def interactive_turn_finished(events):
    """Interactive sessions stay open and need not emit assistant.idle."""
    for index, event in enumerate(events):
        data = event.get("data") or {}
        if event.get("type") == "assistant.message" and data.get("content") and not data.get("toolRequests"):
            if any(later.get("type") == "assistant.turn_end"
                   and (later.get("data") or {}).get("turnId") == data.get("turnId")
                   for later in events[index + 1:]):
                return True
    return False


def ask(sc: dict, model: str | None, *, session_id: str | None = None) -> dict:
    cmd = ["copilot", "--agent", sc.get("agent", "perf-orchestrator"), "-p", sc["prompt"],
           "--allow-all-paths", "--output-format", "json"]
    scaffolded = sc.get("workdir") == "scaffold"
    cmd += (["--allow-all-tools", "--no-ask-user"] if scaffolded
            else ["--available-tools", "view", "glob", "grep", "task"]
                 + (["ask_user"] if sc.get("interactive_cli") and not sc.get("turns") else []))
    if model:
        cmd += ["--model", model]
    if session_id:
        cmd += ["--session-id", session_id]
    with tempfile.TemporaryDirectory() as tmp, ExitStack() as resources:
        cwd = TEMPLATE if sc.get("workdir") == "template" else ROOT
        if scaffolded:
            subprocess.run([sys.executable, str(ROOT / ".github/scripts/scaffold.py"), "sample", "--dest", tmp,
                            "--no-test", "--no-git", *(["--demo"] if sc.get("demo") else [])],
                           check=True, capture_output=True)
            cwd = Path(tmp) / "sample"
        installation = None
        if sc.get("_existing_install"):
            if not scaffolded:
                raise ValueError("Rehearsal installation requires a disposable scaffold")
            subprocess.run(["git", "init", "-q"], cwd=cwd, check=True, capture_output=True)
            from coding_rehearsal import install_in_fixture
            installation = install_in_fixture(cwd)
        mock_url = None
        if sc.get("closed_mock"):
            if not scaffolded or "__MOCK_URL__" not in sc["prompt"]:
                raise ValueError("closed_mock requires a scaffold fixture and __MOCK_URL__")
            reserved = resources.enter_context(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
            reserved.bind(("127.0.0.1", 0))
            # Reserve without listening so the test cannot probe an unrelated local service.
            mock_url = f"http://127.0.0.1:{reserved.getsockname()[1]}"
            cmd[cmd.index("-p") + 1] = sc["prompt"].replace("__MOCK_URL__", mock_url)
        spec = sc.get("trace") or {}
        originals = {f: (cwd / f).read_bytes() for f in spec.get("unchanged_files", [])}
        execute = run_interactive_copilot if sc.get("interactive_cli") else run_copilot
        options = {"resume": sc.get("_interactive_resume", False)} if sc.get("interactive_cli") else {}
        p = execute(cmd, cwd=cwd, timeout=sc.get("_timeout", 900),
                    output_prefix=sc.get("_output_prefix"), cancel_event=sc.get("_cancel"), **options)
        if p.returncode != 0:
            raise RuntimeError(f"copilot exited {p.returncode}: {p.stderr[-2000:]}\n"
                               f"Partial stdout:\n{p.stdout[-2000:]}")
        tr = parse_trace(p.stdout)
        if installation:
            tr["installation"] = installation
        if mock_url:
            tr["mock_url"] = mock_url
        tr["files_missing"] = [f for f in spec.get("files_exist", []) if not (cwd / f).exists()]
        tr["artifact_errors"] = check_artifacts(cwd, spec, originals)
        if spec.get("verify_task_state"):
            if not scaffolded:
                raise ValueError("verify_task_state requires a scaffolded fixture")
            records = list((cwd / ".perf-coding/tasks").glob("*.json"))
            if len(records) != 1:
                tr["artifact_errors"].append(f"expected one persisted coding task, got {len(records)}")
            else:
                check = subprocess.run([sys.executable, ".github/scripts/task_state.py", "show", records[0].stem],
                                       cwd=cwd, capture_output=True, text=True, timeout=30)
                if check.returncode:
                    tr["artifact_errors"].append(f"task-state verification failed: {check.stderr[-1000:]}")
                else:
                    record = json.loads(check.stdout)
                    tr["task_state_result"] = {key: record[key] for key in
                                               ("id", "phase", "contract_revision", "approval", "decision",
                                                "change_summary")}
                    coder = next((r for r in reversed(record["reports"]) if r["role"] == "coder"), None)
                    if coder:
                        tr["task_state_result"]["generator_checks"] = [
                            entry for entry in coder["checks"]
                            if entry["kind"] in ("generator-preview", "generator")
                        ]
                    if record["change_summary"] is None:
                        tr["artifact_errors"].append("persisted task has no pre-edit manifest comparison")
                    if record["phase"] != "accepted":
                        tr["artifact_errors"].append(f"persisted task is not accepted: {record['phase']}")
        tr["artifact_files"] = {f: (cwd / f).read_text(encoding="utf-8")
                                for f in spec.get("file_checks", {}) if (cwd / f).is_file()}
        if spec.get("verify_build"):
            if not scaffolded:
                raise ValueError("verify_build is supported only in a scaffolded fixture")
            build = subprocess.run(["./mvnw", "-q", "test", "detekt:check"], cwd=cwd,
                                   capture_output=True, text=True, timeout=300)
            tr["build_result"] = {"returncode": build.returncode,
                                  "output": (build.stdout + build.stderr)[-4000:] if build.returncode else ""}
        if sc.get("_http_rehearsal"):
            if not scaffolded or not spec.get("verify_build") or tr["build_result"]["returncode"] != 0:
                raise ValueError("HTTP rehearsal requires a passing build in a disposable scaffold")
            if evaluate(sc, tr["answer"]) or evaluate_trace(sc, tr):
                tr["artifact_errors"].append("HTTP rehearsal not run: code/acceptance checks failed")
            else:
                from coding_rehearsal import verify_http
                tr["http_rehearsal"] = verify_http(cwd, sc["_http_rehearsal"], sc.get("_output_prefix"))
                if not tr["http_rehearsal"]["passed"]:
                    tr["artifact_errors"].append("Generated-flow HTTP rehearsal failed: "
                                                 + json.dumps(tr["http_rehearsal"]))
        return tr


def check_artifacts(cwd: Path, spec: dict, originals: dict[str, bytes]) -> list[str]:
    problems = []
    for rel, checks in spec.get("file_checks", {}).items():
        path = cwd / rel
        if not path.is_file():
            problems.append(f"expected file missing: {rel}")
        else:
            problems.extend(f"{rel}: {error}" for error in evaluate(checks, path.read_text(encoding="utf-8")))
    for rel in spec.get("files_absent", []):
        if (cwd / rel).exists():
            problems.append(f"unexpected path created: {rel}")
    for rel, content in originals.items():
        path = cwd / rel
        if not path.is_file() or path.read_bytes() != content:
            problems.append(f"expected unchanged file was modified: {rel}")
    return problems


def parse_trace(stdout: str) -> dict:
    """Final answer, reads (view paths) and sub-agent task prompts from Copilot's JSONL event stream."""
    answer, reads, tasks, tools, agents, models, questions = "", [], [], [], [], [], []
    for line in stdout.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        d = ev.get("data") or {}
        if ev.get("type") != "subagent.started" and d.get("model"):
            models.append({"event": ev.get("type"), "model": d["model"]})
        if ev.get("type") == "assistant.message" and d.get("content"):
            answer = d["content"]
        elif ev.get("type") == "subagent.started":
            agents.append({"model": d.get("model"), "task": d.get("toolCallId"),
                           "name": d.get("agentName")})
        elif ev.get("type") == "tool.execution_start":
            args = d.get("arguments") or {}
            parent = d.get("parentToolCallId") or ev.get("parentToolCallId")
            tool = {"name": d.get("toolName"), "parent": parent}
            if isinstance(args, dict) and isinstance(args.get("command"), str):
                tool["command"] = args["command"]
            tools.append(tool)
            if parent:
                continue
            if d.get("toolName") == "view":
                reads.append(args.get("path", ""))
            elif d.get("toolName") == "task":
                tasks.append(args.get("prompt", ""))
            elif d.get("toolName") == "ask_user":
                questions.append(args.get("question", ""))
    if questions:
        answer = "\n\n".join([answer, *questions]).strip()
    return {"answer": answer, "reads": reads, "tasks": tasks, "tools": tools,
            "agents": agents, "models": models, "questions": questions}


def source_body(path: Path) -> str:
    return re.sub(r"\A# [^\n]*\n+", "", path.read_text(encoding="utf-8")).strip()


def is_task_state_command(command) -> bool:
    """Trace classification, not a shell sandbox or a runtime permission grant."""
    if not isinstance(command, str):
        return False
    command = re.sub(r"\\\r?\n", "", command)
    nonliteral = re.sub(r"'[^']*'", "", command)
    if any(character in nonliteral for character in ("$", "`", "\\", "\n", "\r")):
        return False
    try:
        args = shlex.split(command)
        if len(args) < 4 or args[0] not in {"python", "python3"} or args[1] not in {
            ".github/scripts/task_state.py", "./.github/scripts/task_state.py",
        }:
            return False
        action, task_id = args[2:4]
        if action not in {"init", "show", "patch", "approve", "decline", "intent",
                          "report", "validate-report", "accept"}:
            return False
        if not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", task_id):
            return False
        if action == "show":
            return len(args) == 4
        options = args[4:]
        if len(options) % 2:
            return False
        supplied = {}
        for key, val in zip(options[::2], options[1::2]):
            if key not in {"--data", "--revision"} or key in supplied:
                return False
            supplied[key] = val
        expected = {"--data"} if action == "init" else {"--data", "--revision"}
        return (set(supplied) == expected and isinstance(json.loads(supplied["--data"]), dict)
                and (action == "init" or int(supplied["--revision"]) >= 1))
    except (ValueError, KeyError):
        return False


def evaluate_trace(sc: dict, tr: dict) -> list[str]:
    """Process checks: the orchestrator must build sub-agents from data and verify their work."""
    spec = sc.get("trace")
    if not spec:
        return []
    problems, tasks = [], tr["tasks"]
    if "max_tool_calls" in spec and len(tr.get("tools", [])) > spec["max_tool_calls"]:
        problems.append(f"expected <= {spec['max_tool_calls']} tool call(s), got {len(tr['tools'])}")
    if "only_tools" in spec:
        for tool in tr.get("tools", []):
            if (tool["name"] or "").split(".")[-1] not in spec["only_tools"]:
                problems.append(f"unexpected tool for this interaction: {tool['name']}")
    if spec.get("no_history_search"):
        for tool in tr.get("tools", []):
            if (tool["name"] or "").split(".")[-1] == "session_store_sql":
                problems.append("unnecessary session-history search in a self-contained task")
    root = TEMPLATE if sc.get("agent") == "perf-coding" else ROOT
    skill = "perf-coding" if sc.get("agent") == "perf-coding" else "perf-setup"
    if spec.get("orchestrator_read_only"):
        forbidden = {"bash", "powershell", "terminal", "execute", "edit", "create",
                     "apply_patch", "read_bash", "stop_bash", "write_file"}
        for tool in tr.get("tools", []):
            name = (tool["name"] or "").split(".")[-1]
            if not tool["parent"] and name in forbidden:
                if (spec.get("allow_task_state") and sc.get("agent") == "perf-coding"
                        and name in {"bash", "execute"} and is_task_state_command(tool.get("command"))):
                    continue
                problems.append(f"orchestrator directly called {name}")
    if len(tasks) < spec.get("min_subagents", 1):
        problems.append(f"expected >= {spec.get('min_subagents', 1)} sub-agent(s), got {len(tasks)}")
    if "max_subagents" in spec and len(tasks) > spec["max_subagents"]:
        problems.append(f"expected <= {spec['max_subagents']} sub-agent(s), got {len(tasks)}")
    for rel in spec.get("reads", []):
        if any(rel in r for r in tr["reads"]):
            continue
        candidates = [root / rel, root / ".github/skills" / rel, root / ".github/skills" / skill / rel]
        embedded = False
        for path in candidates:
            if path.is_file():
                # A document title may be relabeled; every body line must still be literal.
                source = source_body(path)
                if source and any(source in task for task in tasks):
                    embedded = True
                    break
        if not embedded:
            problems.append(f"no observed read or full source in tasks: {rel}")
    if spec.get("rules_in_task") or spec.get("rules_in_reviewer"):
        rules = source_body(root / ".github/skills" / skill / "rules.md")
        if spec.get("rules_in_task") and (not tasks or any(rules not in task for task in tasks)):
            problems.append("full rules.md body is not embedded in every sub-agent task")
        if spec.get("rules_in_reviewer") and not any("VERDICT" in x and rules in x for x in tasks):
            problems.append("the reviewer task does not carry full rules.md")
    problems += [f"expected file missing: {f}" for f in tr.get("files_missing", [])]
    problems += tr.get("artifact_errors", [])
    if spec.get("verify_build"):
        build = tr.get("build_result")
        if build is None:
            problems.append("independent Maven verification did not run")
        elif build["returncode"] != 0:
            problems.append(f"Maven test/detekt failed ({build['returncode']}): {build['output']}")
    if spec.get("reviewer") and not any("VERDICT" in x for x in tasks):
        problems.append("no reviewer sub-agent was spawned (no task asks for a VERDICT)")
    return problems


def evaluate(sc: dict, answer: str) -> list[str]:
    problems = []
    if not answer.strip():
        problems.append("empty assistant answer")
    # URL query delimiters are not questions in the user-facing prose.
    prose = re.sub(r"https?://[^\s<>]*[^\s<>.,;:!?)]", "", answer)
    if sc.get("requires_input"):
        plain = re.sub(r"[*`#]", "", prose)
        imperative = re.search(
            r"(?:^|[.!:\n]\s*)(?:(?:first|next|now|then),?\s+)?(?:please\s+)?"
            r"(?:choose|select|pick|identify|tell me|let me know|provide|specify|enter|confirm)\b",
            plain, re.I,
        )
        if "?" not in prose and not imperative:
            problems.append("missing explicit request for user input")
    if "max_questions" in sc and prose.count("?") > sc["max_questions"]:
        problems.append(f"more than {sc['max_questions']} question(s)")
    if "max_words" in sc and len(answer.split()) > sc["max_words"]:
        problems.append(f"more than {sc['max_words']} words")
    for pat in sc.get("must", []):
        if not re.search(pat, answer, re.I):
            problems.append(f"missing: /{pat}/")
    for pat in sc.get("must_not", []):
        m = re.search(pat, answer, re.I)
        if m:
            problems.append(f"forbidden: /{pat}/ matched '{m.group(0)[:60]}'")
    for command in sc.get("forbidden_commands", []):
        for match in re.finditer(re.escape(command), answer, re.I):
            # A warning not to run a command is not a recommendation to run it.
            clause = re.split(r"[.!?;\n]", answer[:match.start()])[-1]
            if not re.search(r"\b(?:do not|don['’]t|never|must not|cannot|can['’]t|will not|won['’]t)\b[^.!?;\n]*$",
                             clause, re.I):
                problems.append(f"forbidden command recommendation: {command}")
    return problems


def run_one(sc: dict, runs: int, model: str | None, log_dir: Path | None = None):
    results = []
    turns = sc.get("turns") or [sc]
    for run_number in range(1, runs + 1):
        if sc.get("_cancel") is not None and sc["_cancel"].is_set():
            return sc["id"], results + [(["cancelled before starting next run"], "")]
        label = f"{sc['id']} run {run_number}/{runs}"
        print(f"START {label} ({len(turns)} turns)", flush=True)
        # One fresh session per run; each turn resumes exactly that conversation.
        session_id = str(uuid.uuid4())
        transcript, problems = [], []
        log_path = None
        if log_dir is not None:
            safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", sc["id"])
            log_path = log_dir / f"{safe_id}-run-{run_number}.md"
            log_path.write_text(f"# {sc['id']} — run {run_number}\n\n"
                                f"Session: {session_id or 'single turn'}\n\n"
                                f"Requested model: {model or 'agent default (not pinned)'}\n\n"
                                f"CLI version: {sc.get('_cli_version', 'not recorded')}\n\n",
                                encoding="utf-8")

        def append_log(text):
            if log_path is not None:
                with log_path.open("a", encoding="utf-8") as log:
                    log.write(text)

        try:
            for number, turn in enumerate(turns, 1):
                if sc.get("_cancel") is not None and sc["_cancel"].is_set():
                    raise RuntimeError("cancelled before starting next turn")
                request = {**sc, **turn}
                if sc.get("interactive_cli"):
                    request["_interactive_resume"] = number > 1
                if log_path:
                    request["_output_prefix"] = log_dir / f"{safe_id}-run-{run_number}-turn-{number}"
                if sc.get("turns"):
                    for key in ("must", "must_not"):
                        request[key] = sc.get(key, []) + turn.get(key, [])
                print(f"WAIT  {label} turn {number}/{len(turns)}: waiting for Copilot "
                      f"(CLI timeout {request.get('_timeout', 900)}s)", flush=True)
                started = time.monotonic()
                append_log(f"## Turn {number}\n\n### User\n\n{request['prompt']}\n\n")
                tr = ask(request, model, session_id=session_id)
                errors = evaluate(request, tr["answer"]) + evaluate_trace(request, tr)
                problems.extend(f"turn {number}: {error}" for error in errors)
                transcript.append(f"USER: {request['prompt']}\nASSISTANT: {tr['answer']}")
                append_log(f"### Assistant\n\n{tr['answer']}\n\n"
                           f"**{'FAIL' if errors else 'PASS'}** "
                           f"({time.monotonic() - started:.1f}s)\n\n"
                           + "".join(f"- {error}\n" for error in errors) + "\n")
                append_log("Reported model events: "
                           + json.dumps(tr.get("models") or [], ensure_ascii=True)
                           + " (empty means unreported; not inferred).\n\n")
                if "build_result" in tr:
                    append_log(f"Independent fixture check: `./mvnw -q test detekt:check`, "
                               f"exit {tr['build_result']['returncode']}.\n\n")
                if tr.get("task_state_result"):
                    append_log("### Persisted task acceptance\n\n```json\n"
                               + json.dumps(tr["task_state_result"], indent=2) + "\n```\n\n")
                for key in ("installation", "http_rehearsal"):
                    if key in tr:
                        append_log(f"### {key}\n\n```json\n"
                                   + json.dumps(tr[key], indent=2) + "\n```\n\n")
                if tr.get("mock_url"):
                    append_log(f"Reserved, non-listening fixture target: `{tr['mock_url']}`.\n\n")
                if tr.get("agents"):
                    append_log("### Worker models reported by CLI\n\n```json\n"
                               + json.dumps(tr["agents"], indent=2) + "\n```\n\n")
                if tr.get("artifact_files"):
                    append_log("### Checked fixture files\n\n")
                    for path, content in tr["artifact_files"].items():
                        append_log(f"#### {path}\n\n````text\n{content}\n````\n\n")
                if errors and request.get("trace") and tr["tasks"]:
                    append_log("### Delegation prompts for failed checks\n\n")
                    for task_number, prompt in enumerate(tr["tasks"], 1):
                        append_log(f"#### Task {task_number}\n\n````text\n{prompt}\n````\n\n")
                if request.get("trace") and tr.get("tools"):
                    append_log("### Tool ownership\n\n```json\n"
                               + json.dumps(tr["tools"], indent=2) + "\n```\n\n")
                print(f"{'FAIL' if errors else 'PASS'}  {label} turn {number}/{len(turns)} "
                      f"({time.monotonic() - started:.1f}s)", flush=True)
                if errors:
                    break
            results.append((problems, "\n\n".join(transcript)))
        except Exception as exc:  # noqa: BLE001
            append_log(f"\n**ERROR:** {exc}\n")
            append_log("\n```text\n" + traceback.format_exc() + "\n```\n")
            print(f"ERROR {label}: {exc}", flush=True)
            results.append((problems + [f"error: {exc}"], "\n\n".join(transcript)))
        except KeyboardInterrupt:
            append_log("\n**INTERRUPTED:** no completed response for the current turn.\n")
            raise
        append_log(f"\n## Result: {'FAIL' if results[-1][0] else 'PASS'}\n")
        print(f"DONE  {label}: {'FAIL' if results[-1][0] else 'PASS'}", flush=True)
    return sc["id"], results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--model")
    ap.add_argument("--timeout", type=float, default=900,
                    help="maximum CLI seconds per turn; keeps partial output and stops its process tree")
    ap.add_argument("-j", type=int, default=4)
    ap.add_argument("--slow", action="store_true", help="include scenarios that run in a scaffolded repo with all tools")
    ap.add_argument("--onboarding", action="store_true", help="run the opt-in multi-turn onboarding matrix")
    ap.add_argument("--rehearsal", action="store_true",
                    help="explicitly approve two disposable implementation fixtures plus owned loopback HTTP "
                         "(at most 2 users, 10 seconds each); existing path tests agent installation")
    ap.add_argument("--list", action="store_true", help="list selected scenarios without invoking the model")
    ap.add_argument("-v", action="store_true", help="print answers of failed runs")
    ap.add_argument("--log-dir", type=Path,
                    help="parent directory for conversation logs (default: tests/results)")
    a = ap.parse_args()
    if a.runs < 1 or a.j < 1:
        ap.error("--runs and -j must be positive")
    if not math.isfinite(a.timeout) or a.timeout <= 0:
        ap.error("--timeout must be a finite positive number")
    if a.rehearsal and a.onboarding:
        ap.error("--rehearsal cannot be combined with --onboarding")
    scenarios = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    if a.onboarding:
        from onboarding_scenarios import build_scenarios
        scenarios = build_scenarios()
    if a.rehearsal:
        kinds = {"coding-agent-adds-domain-end-to-end": "orders",
                 "coding-agent-extends-domain-end-to-end": "items"}
        scenarios = [{**sc, "_http_rehearsal": kinds[sc["id"]],
                      "_existing_install": kinds[sc["id"]] == "items"}
                     for sc in scenarios if sc["id"] in kinds]
        if not a.only:
            a.only = list(kinds)
    if a.only:
        unknown = set(a.only) - {s["id"] for s in scenarios}
        if unknown:
            ap.error("unknown scenario IDs: " + ", ".join(sorted(unknown)))
    scenarios = [s for s in scenarios if (a.only and s["id"] in a.only) or
                 (not a.only and (a.slow or not s.get("slow")))]
    if a.list:
        for sc in scenarios:
            print(f"{sc['id']} ({len(sc.get('turns') or [sc])} turns)")
        return 0
    if a.j > 1 and any(sc.get("interactive_cli") for sc in scenarios):
        ap.error("native interactive scenarios require -j 1; parallel PTY execution is unsupported")
    if not shutil.which("copilot"):
        print("copilot CLI not found", file=sys.stderr)
        return 2
    version = subprocess.run(["copilot", "--version"], capture_output=True, text=True,
                             timeout=10, check=True).stdout.strip()
    cancel = Event()
    scenarios = [{**sc, "_timeout": a.timeout, "_cli_version": version, "_cancel": cancel}
                 for sc in scenarios]
    log_root = a.log_dir or ROOT / "tests/results"
    log_root.mkdir(parents=True, exist_ok=True)
    log_dir = Path(tempfile.mkdtemp(
        prefix=datetime.now().strftime("%Y%m%d-%H%M%S-"), dir=log_root))
    print(f"Conversation logs: {log_dir}", flush=True)
    with ThreadPoolExecutor(max_workers=a.j) as ex:
        try:
            outcomes = list(ex.map(lambda s: run_one(s, a.runs, a.model, log_dir), scenarios))
        except KeyboardInterrupt:
            cancel.set()
            ex.shutdown(wait=True, cancel_futures=True)
            print(f"Interrupted; active CLI processes stopped. Partial logs: {log_dir}", file=sys.stderr)
            return 130
    failed = 0
    for sid, results in outcomes:
        bad = [r for r in results if r[0]]
        print(f"{'FAIL' if bad else 'PASS'}  {sid}  ({len(results) - len(bad)}/{len(results)} runs)")
        for problems, ans in bad:
            failed += 1
            for pr in problems:
                print(f"      - {pr}")
            if a.v and ans:
                print("      ---- transcript ----\n" + "\n".join("      " + l for l in ans.splitlines()))
    print(f"\n{len(outcomes)} scenario(s), {sum(1 for _, r in outcomes if any(x[0] for x in r))} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

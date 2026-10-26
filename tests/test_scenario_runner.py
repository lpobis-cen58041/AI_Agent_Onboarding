"""Test matrix coverage and session handling without model calls or credits."""
import importlib.util
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, TESTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = load_module("run_scenarios")
matrix = load_module("onboarding_scenarios")


def test_all_valid_decision_combinations_are_covered():
    scenarios = matrix.build_scenarios()
    assert len(scenarios) == 18
    assert len({sc["id"] for sc in scenarios}) == 18
    for situation in ("joining", "starting"):
        for resource in ("repo-exists", "sas-only", "no-sas"):
            for permission in ("granted", "missing", "pending"):
                assert any(sc["id"] == f"onboarding-{situation}-{resource}-{permission}"
                           for sc in scenarios)
    for sc in scenarios:
        assert 4 <= len(sc["turns"]) <= 7
        for turn in sc["turns"]:
            assert turn["prompt"]
            assert turn["must"]
            for regex in sc["must_not"] + turn.get("must_not", []) + turn["must"]:
                runner.re.compile(regex)


def test_contributor_turns_keep_limits_and_check_content_not_just_length():
    for sc in matrix.build_scenarios():
        assert sc["max_words"] == 240
        contributor = sc["turns"][2 if "-repo-exists-" in sc["id"] else -2]
        assert contributor["max_words"] == 160
        assert set(matrix.CONTRIBUTOR_SCOPE) <= set(contributor["must_not"])
        app = "GEORGEPETE" if "-repo-exists-" in sc["id"] else "ONBOARDING_DEMO"
        answer = (f"The project guidance lists CSIN\\GHB_DEV_{app}_WRITE for contributing "
                  "code. Request it in REDiM under Windows if you do not already have it. "
                  "Would you like help with the request?")
        spec = {**sc, **contributor, "must_not": sc["must_not"] + contributor["must_not"]}
        assert runner.evaluate(spec, answer) == []
        # Even a short list must fail if it adds unrelated services or claims verification.
        for extra in ("CSIN\\ART_GEORGEPETE_DELETE", "CSIN\\GeorgePete_Viewer",
                      "XUC\\APIMAN_DEVELOPER", "CSINT\\Alfred_Authentication_Users",
                      f"CSIN\\GHB_DEV_{app}_ADM", "I verified these permissions."):
            assert runner.evaluate(spec, answer + " " + extra)


def test_turns_resume_same_session_and_runs_are_isolated(monkeypatch):
    calls = []

    def ask(sc, model, *, session_id):
        calls.append((sc["prompt"], session_id))
        return {"answer": "Ready.", "reads": [], "tasks": []}

    monkeypatch.setattr(runner, "ask", ask)
    sc = {"id": "conversation", "turns": [
        {"prompt": "First", "must": ["Ready"]},
        {"prompt": "Second", "must": ["Ready"]},
    ]}
    _, results = runner.run_one(sc, 2, None)
    assert all(not errors for errors, _ in results)
    assert calls[0][1] == calls[1][1]
    assert calls[2][1] == calls[3][1]
    assert calls[0][1] != calls[2][1]
    assert [prompt for prompt, _ in calls] == ["First", "Second", "First", "Second"]


def test_global_and_turn_checks_both_apply_and_stop_on_failure(monkeypatch):
    calls = []

    def ask(sc, model, **kwargs):
        calls.append(sc)
        return {"answer": "global-bad turn-bad", "reads": [], "tasks": []}

    monkeypatch.setattr(runner, "ask", ask)
    sc = {"id": "bad", "must_not": ["global-bad"], "turns": [
        {"prompt": "First", "must_not": ["turn-bad"]},
        {"prompt": "Must not be sent"},
    ]}
    _, results = runner.run_one(sc, 1, None)
    assert len(calls) == 1
    assert len(results[0][0]) == 2
    assert all(error.startswith("turn 1:") for error in results[0][0])
    assert "USER: First" in results[0][1]


@pytest.mark.parametrize("answer", ["", "   ", "One? Two?", "one two three"])
def test_empty_or_overlong_answers_and_multiple_questions_fail(answer):
    assert runner.evaluate({"max_questions": 1, "max_words": 2}, answer)


@pytest.mark.parametrize("answer", [
    "See [guide](https://example.test/page?id=123). Shall we continue?",
    "See https://example.test/page?id=123&view=full and "
    "[form](https://example.test/sp?id=form&sys_id=abc). Ready?",
    "See <https://example.test/page?id=123>. Ready?",
])
def test_url_queries_are_not_user_questions(answer):
    assert runner.evaluate({"max_questions": 1}, answer) == []


def test_real_multiple_questions_still_fail_with_links():
    answer = "See [guide](https://example.test/page?id=123). Does it exist? What is its ID?"
    assert runner.evaluate({"max_questions": 1}, answer) == ["more than 1 question(s)"]


@pytest.mark.parametrize("answer", [
    "What status should GET /orders return?",
    "Next, choose the **expected HTTP status code** for `GET /orders`.",
    "First, choose whether to create a new domain or extend an existing domain.",
    "Now, please provide the domain name.",
    "Please confirm whether I should implement the agreed change.",
    "Identify the repository containing reports, or select the existing domain.",
])
def test_input_can_be_requested_as_a_question_or_imperative(answer):
    assert runner.evaluate({"requires_input": True, "max_questions": 1}, answer) == []


@pytest.mark.parametrize("answer", [
    "The expected status is not known.",
    "I will choose the expected status later.",
    "Here's the agreed plan. Implementation remains paused.",
    "The status is documented at https://example.test/guide?id=123.",
    "The next step is to identify the repository containing reports.",
])
def test_summary_without_input_request_does_not_advance_intake(answer):
    assert runner.evaluate({"requires_input": True}, answer) == ["missing explicit request for user input"]


def test_checkout_followup_is_a_second_question():
    spec = {"max_questions": 1}
    answer = ("Have you already copied (cloned) the repository to your computer? "
              "If so, which folder is it in?")
    assert runner.evaluate(spec, answer) == ["more than 1 question(s)"]
    assert runner.evaluate(spec, "What is the local folder of the cloned repository? "
                           "If it is not cloned yet, say so.") == []


def test_missing_repo_fixtures_do_not_reuse_existing_reference_project():
    for scenario in matrix.build_scenarios():
        if "-repo-exists-" in scenario["id"]:
            continue
        prompts = "\n".join(turn["prompt"] for turn in scenario["turns"])
        assert "GEORGEPETE" not in prompts
        assert "SAS_ONBOARDING_DEMO" in prompts
        assert "exact contributor group is CSIN\\GHB_DEV_ONBOARDING_DEMO_WRITE" in prompts


@pytest.mark.parametrize("answer", [
    "The form adds the application part from the SAS, so don't type it.",
    "The prefix is added automatically.",
    "The application name is added by the form.",
])
def test_prefix_rule_accepts_equivalent_explanations(answer):
    assert runner.evaluate({"must": [matrix.AUTOMATIC_PREFIX]}, answer) == []


def test_prefix_rule_still_requires_an_explanation():
    assert runner.evaluate({"must": [matrix.AUTOMATIC_PREFIX]},
                           "Choose SAS and enter pete-automation.")


@pytest.mark.parametrize("answer", [
    "Do not use `gh repo create`.",
    "Don't create it directly in GitHub or with `gh repo create`.",
    "Never run gh repo create for this project.",
    "It won't create a new repository or run gh repo create.",
    "We will not run gh repo create.",
    "We won’t use gh repo create.",
])
def test_command_prohibition_is_not_a_recommendation(answer):
    assert not runner.evaluate({"forbidden_commands": ["gh repo create"]}, answer)


@pytest.mark.parametrize("answer", [
    "Run gh repo create now.",
    "Do not wait. Run gh repo create.",
    "Don't use the form; use gh repo create instead.",
    "We won't change permissions. Run gh repo create.",
])
def test_actual_forbidden_command_recommendations_fail(answer):
    assert runner.evaluate({"forbidden_commands": ["gh repo create"]}, answer)


def test_cli_session_id_is_passed_with_read_only_tool_selection(monkeypatch):
    commands = []

    def run(cmd, **kwargs):
        commands.append(cmd)
        return runner.subprocess.CompletedProcess(
            cmd, 0, '{"type":"assistant.message","data":{"content":"Ready."}}\n', ""
        )

    monkeypatch.setattr(runner, "run_copilot", run)
    assert runner.ask({"prompt": "Hello"}, None, session_id="test-session")["answer"] == "Ready."
    cmd = commands[0]
    assert cmd[cmd.index("--session-id") + 1] == "test-session"
    assert "--available-tools" in cmd
    assert "--allow-all-tools" not in cmd
    assert "--no-ask-user" not in cmd
    assert "ask_user" not in cmd


def test_coding_guidance_uses_template_with_read_only_tools(monkeypatch):
    calls = []

    def run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return runner.subprocess.CompletedProcess(
            cmd, 0, '{"type":"assistant.message","data":{"content":"Ready."}}\n', ""
        )

    monkeypatch.setattr(runner, "run_copilot", run)
    runner.ask({"agent": "perf-coding", "workdir": "template", "prompt": "Explain only"}, None)
    cmd, kwargs = calls[0]
    assert kwargs["cwd"] == runner.TEMPLATE
    assert cmd[cmd.index("--agent") + 1] == "perf-coding"
    assert "--allow-all-tools" not in cmd
    assert "--available-tools" in cmd
    assert "--no-ask-user" not in cmd
    assert "ask_user" not in cmd


def test_artifact_checks_detect_missing_behavior_and_unrelated_changes(tmp_path):
    path = tmp_path / "requests.kt"
    path.write_text("getItems getItemDetail")
    keep = tmp_path / "ci.csv"
    keep.write_text("existing simulation\n")
    originals = {"ci.csv": keep.read_bytes()}
    spec = {"file_checks": {"requests.kt": {"must": ["getItems", "getItemDetail"]}},
            "files_absent": ["domain/replacement"], "unchanged_files": ["ci.csv"]}
    assert runner.check_artifacts(tmp_path, spec, originals) == []
    path.write_text("getItemDetail")
    assert any("getItems" in e for e in runner.check_artifacts(tmp_path, spec, originals))
    path.unlink()
    assert any("expected file missing" in e for e in runner.check_artifacts(tmp_path, spec, originals))
    keep.write_text("duplicate simulation\n")
    (tmp_path / "domain/replacement").mkdir(parents=True)
    errors = runner.check_artifacts(tmp_path, spec, originals)
    assert any("unchanged file was modified" in e for e in errors)
    assert any("unexpected path created" in e for e in errors)


def test_uniqueness_gate_accepts_distinct_and_set_but_not_missing_check():
    scenarios = runner.json.loads(runner.SCENARIOS.read_text(encoding="utf-8"))
    scenario = next(sc for sc in scenarios if sc["id"] == "coding-agent-extends-domain-end-to-end")
    checks = scenario["trace"]["file_checks"]["src/test/kotlin/cz/example/perf/setup/WeightSumTest.kt"]
    common = 'assertEquals(listOf("browseItems", "viewItemDetails"), names); assertEquals(listOf(70, 30), weights)'
    for operation in ("distinct()", "toSet()"):
        assert not runner.evaluate(checks, common + f"; assertEquals(2, names.{operation}.size)")
    assert runner.evaluate(checks, common)


def test_native_interview_routes_to_interactive_cli_with_question_tool(monkeypatch):
    calls = []

    def run(cmd, **kwargs):
        calls.append(cmd)
        return runner.subprocess.CompletedProcess(
            cmd, 0, '{"type":"tool.execution_start","data":{"toolName":"ask_user",'
            '"arguments":{"question":"Which repository contains reports?"}}}\n', ""
        )

    monkeypatch.setattr(runner, "run_interactive_copilot", run)
    monkeypatch.setattr(runner, "run_copilot", lambda *args, **kwargs: pytest.fail("autonomous CLI used"))
    result = runner.ask({"prompt": "Missing domain", "workdir": "template", "interactive_cli": True},
                        None, session_id="fresh-test")
    assert result["questions"] == ["Which repository contains reports?"]
    assert "ask_user" in calls[0]
    assert "--no-ask-user" not in calls[0]


def test_successful_model_answer_does_not_override_failed_build():
    sc = {"trace": {"min_subagents": 0, "verify_build": True}}
    trace = {"answer": "All tests passed.", "tasks": [], "reads": [],
             "build_result": {"returncode": 1, "output": "Compilation failed"}}
    assert runner.evaluate_trace(sc, trace) == ["Maven test/detekt failed (1): Compilation failed"]
    trace.pop("build_result")
    assert runner.evaluate_trace(sc, trace) == ["independent Maven verification did not run"]
    trace["build_result"] = {"returncode": 0, "output": ""}
    assert runner.evaluate_trace(sc, trace) == []


def test_source_evidence_accepts_full_text_not_just_a_path(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "TEMPLATE", tmp_path)
    source = tmp_path / ".github/skills/perf-coding/rules.md"
    source.parent.mkdir(parents=True)
    body = "These are the full source rules.\nKeep every sentence.\n"
    source.write_text("# Rules\n\n" + body)
    sc = {"agent": "perf-coding", "trace": {"reads": ["perf-coding/rules.md"]}}
    trace = {"reads": [], "tasks": ["Read .github/skills/perf-coding/rules.md"]}
    assert runner.evaluate_trace(sc, trace)
    trace["tasks"] = ["Rules:\n" + source.read_text() + "\nTask: review."]
    assert runner.evaluate_trace(sc, trace) == []
    trace["tasks"] = ["Relabeled rules:\n" + body]
    assert runner.evaluate_trace(sc, trace) == []
    trace["tasks"] = ["These are the full source rules."]
    assert runner.evaluate_trace(sc, trace)
    trace["reads"] = [str(source)]
    assert runner.evaluate_trace(sc, trace) == []


@pytest.mark.parametrize("demo", [False, True])
@pytest.mark.parametrize("existing_install", [False, True])
def test_scaffold_build_verification_runs_before_cleanup(monkeypatch, demo, existing_install):
    import coding_rehearsal

    calls = []

    def run(cmd, **kwargs):
        calls.append(cmd)
        if "scaffold.py" in cmd[1]:
            root = Path(cmd[cmd.index("--dest") + 1]) / "sample"
            root.mkdir()
            (root / "fixture.kt").write_text("original")
            return runner.subprocess.CompletedProcess(cmd, 0, "", "")
        if cmd == ["git", "init", "-q"]:
            (kwargs["cwd"] / ".git").mkdir()
            return runner.subprocess.CompletedProcess(cmd, 0, "", "")
        if cmd[0] == "copilot":
            (kwargs["cwd"] / "fixture.kt").write_text("new behavior")
            return runner.subprocess.CompletedProcess(
                cmd, 0, '{"type":"assistant.message","data":{"content":"Done."}}\n', ""
            )
        assert (kwargs["cwd"] / "fixture.kt").read_text() == "new behavior"
        assert kwargs["timeout"] == 300
        return runner.subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(runner.subprocess, "run", run)
    monkeypatch.setattr(runner, "run_copilot", run)

    def install(checkout):
        assert (checkout / ".git").is_dir()
        assert (checkout / "fixture.kt").read_text() == "original"
        return {"added": ["agent"]}

    monkeypatch.setattr(coding_rehearsal, "install_in_fixture", install)
    result = runner.ask({"prompt": "Change", "workdir": "scaffold", "demo": demo,
                        "_existing_install": existing_install, "trace": {
        "verify_build": True, "file_checks": {"fixture.kt": {"must": ["new behavior"]}},
    }}, None)
    assert calls[-1] == ["./mvnw", "-q", "test", "detekt:check"]
    assert ("--demo" in calls[0]) == demo
    assert "--no-git" in calls[0]
    assert (["git", "init", "-q"] in calls) == existing_install
    assert ("installation" in result) == existing_install
    assert "--allow-all-tools" in calls[-2]
    assert "--no-ask-user" in calls[-2]
    assert result["artifact_errors"] == []
    assert result["artifact_files"] == {"fixture.kt": "new behavior"}
    assert result["build_result"]["returncode"] == 0


@pytest.mark.parametrize("accepted", [True, False])
def test_http_rehearsal_requires_passing_artifact_and_acceptance_gates(monkeypatch, accepted):
    import coding_rehearsal

    traffic = []

    def run(cmd, **kwargs):
        if len(cmd) > 1 and "scaffold.py" in cmd[1]:
            (Path(cmd[cmd.index("--dest") + 1]) / "sample").mkdir()
        return runner.subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(runner.subprocess, "run", run)
    monkeypatch.setattr(runner, "run_copilot", lambda *args, **kwargs:
                        runner.subprocess.CompletedProcess(
                            [], 0, '{"type":"assistant.message","data":{"content":"Done."}}\n', ""))
    monkeypatch.setattr(runner, "evaluate_trace", lambda *args: [] if accepted else ["not accepted"])

    def http(checkout, kind, prefix):
        assert checkout.is_dir()
        traffic.append(kind)
        return {"passed": True}

    monkeypatch.setattr(coding_rehearsal, "verify_http", http)
    result = runner.ask({"prompt": "Change", "workdir": "scaffold", "_http_rehearsal": "orders",
                         "trace": {"verify_build": True}}, None)
    assert traffic == (["orders"] if accepted else [])
    assert ("http_rehearsal" in result) == accepted
    if not accepted:
        assert result["artifact_errors"] == ["HTTP rehearsal not run: code/acceptance checks failed"]


def test_rehearsal_selection_is_explicit_and_cannot_include_onboarding(monkeypatch, capsys):
    monkeypatch.setattr(runner.sys, "argv", ["run_scenarios.py", "--rehearsal", "--list"])
    assert runner.main() == 0
    assert capsys.readouterr().out.splitlines() == [
        "coding-agent-adds-domain-end-to-end (1 turns)",
        "coding-agent-extends-domain-end-to-end (1 turns)",
    ]
    monkeypatch.setattr(runner.sys, "argv",
                        ["run_scenarios.py", "--rehearsal", "--onboarding", "--list"])
    with pytest.raises(SystemExit, match="2"):
        runner.main()


def test_failed_generated_http_is_not_a_passing_rehearsal(tmp_path, monkeypatch):
    import coding_rehearsal

    def run(cmd, **kwargs):
        if len(cmd) > 1 and "scaffold.py" in cmd[1]:
            (Path(cmd[cmd.index("--dest") + 1]) / "sample").mkdir()
        return runner.subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(runner.subprocess, "run", run)
    monkeypatch.setattr(runner, "run_copilot", lambda *args, **kwargs:
                        runner.subprocess.CompletedProcess(
                            [], 0, '{"type":"assistant.message","data":{"content":"Done."}}\n', ""))
    monkeypatch.setattr(coding_rehearsal, "verify_http",
                        lambda *args: {"passed": False, "observed_requests": {}})
    result = runner.ask({"prompt": "Change", "workdir": "scaffold", "_http_rehearsal": "orders",
                         "trace": {"min_subagents": 0, "verify_build": True}}, None)
    assert any("Generated-flow HTTP rehearsal failed" in error for error in result["artifact_errors"])


def test_coding_scenarios_cover_guidance_and_both_implementation_paths():
    scenarios = runner.json.loads(runner.SCENARIOS.read_text(encoding="utf-8"))
    coding = [sc for sc in scenarios if sc.get("agent") == "perf-coding"]
    assert len(coding) == 36
    assert {"coding-test-readiness-after-mock", "coding-test-from-laptop", "coding-prod-readiness"} <= {
        sc["id"] for sc in coding
    }
    for sc in coding:
        if sc["id"] in {"coding-test-readiness-after-mock", "coding-test-from-laptop", "coding-prod-readiness"}:
            assert sc["max_words"] == 180
    for sc in coding:
        if sc["workdir"] == "scaffold":
            assert sc["slow"]
            if not sc.get("closed_mock"):
                assert sc["trace"]["verify_build"]
                assert sc["trace"]["file_checks"]
            assert sc["trace"]["unchanged_files"]
        else:
            assert sc["workdir"] == "template"
            assert sc["max_questions"] == 1
        for checks in [sc, *sc.get("turns", []), *(sc.get("trace") or {}).get("file_checks", {}).values()]:
            for regex in checks.get("must", []) + checks.get("must_not", []):
                runner.re.compile(regex)


def test_coding_startup_needs_no_coaching_or_repository_audit():
    scenarios = runner.json.loads(runner.SCENARIOS.read_text(encoding="utf-8"))
    startup = [sc for sc in scenarios if sc["id"] in {"coding-startup", "coding-greeting"}]
    assert {sc["prompt"] for sc in startup} == {"Start", "Hi"}
    answer = "Would you like to create a new domain or add/change tests in an existing domain?"
    for sc in startup:
        assert sc["interactive_cli"]
        assert not runner.evaluate(sc, answer)
        assert runner.evaluate(sc, "I recommend improving .github/copilot-instructions.md.")
        assert runner.evaluate(sc, "Hi! I can help you create a new domain or add/change tests in an existing domain.")
        assert not runner.evaluate_trace(sc, {"reads": [], "tasks": [], "tools": []})
        assert not runner.evaluate_trace(sc, {"reads": [], "tasks": [],
                                             "tools": [{"name": "ask_user", "parent": None}]})
        assert runner.evaluate_trace(sc, {"reads": ["README.md"], "tasks": [],
                                         "tools": [{"name": "view", "parent": None}]})
        assert runner.evaluate_trace(sc, {"reads": [], "tasks": ["Audit the repo"], "tools": []})


def test_interactive_coding_intake_requires_no_delegation():
    scenarios = runner.json.loads(runner.SCENARIOS.read_text(encoding="utf-8"))
    interactive = [s for s in scenarios if s["id"].startswith("coding-interactive-")]
    assert len(interactive) == 2
    for sc in interactive:
        assert sc["workdir"] == "template"
        assert len(sc["turns"]) >= 5
        assert runner.evaluate_trace(sc, {"reads": [], "tasks": []}) == []
        assert runner.evaluate_trace(sc, {"reads": [], "tasks": ["Implement early"]})
        assert "No" in sc["turns"][-1]["prompt"]
    new = next(sc for sc in interactive if sc["id"].endswith("new-domain"))
    assert any("correct" in t["prompt"] for t in new["turns"])


def test_endpoint_scenarios_cover_conditional_intake_without_execution():
    scenarios = runner.json.loads(runner.SCENARIOS.read_text(encoding="utf-8"))
    endpoints = {s["id"]: s for s in scenarios if s["id"].startswith("coding-endpoint-")}
    assert set(endpoints) == {
        "coding-endpoint-json-patch-intake", "coding-endpoint-public-text",
        "coding-endpoint-gateway-channel", "coding-endpoint-availability-variants",
        "coding-endpoint-head", "coding-endpoint-multipart",
        "coding-endpoint-get-query", "coding-endpoint-post-json", "coding-endpoint-put-json",
        "coding-endpoint-delete-204", "coding-endpoint-options", "coding-endpoint-form-urlencoded",
        "coding-endpoint-unknown-content-type", "coding-endpoint-202-polling",
        "coding-endpoint-mixed-profiles",
    }
    for sc in endpoints.values():
        assert sc["workdir"] == "template"
        assert sc["trace"]["no_history_search"]
        assert not runner.evaluate_trace(sc, {"reads": [], "tasks": [], "tools": []})
        assert runner.evaluate_trace(sc, {"reads": [], "tasks": ["Implement before approval"], "tools": []})
    patch = endpoints["coding-endpoint-json-patch-intake"]
    assert not runner.evaluate(patch["turns"][0], "What relative endpoint path should the request use?")
    assert runner.evaluate(patch["turns"][0], "What HTTP method should it use?")
    assert not runner.evaluate(patch["turns"][1], "What HTTP status should PATCH /items/{itemId} return?")
    assert runner.evaluate(patch["turns"][1], "What JSON body should it send?")
    availability = endpoints["coding-endpoint-availability-variants"]["turns"]
    assert not runner.evaluate(availability[1], "What riskLevel.recommended value is defined for this type?")
    assert runner.evaluate(availability[1], "Use 1 for riskLevel.recommended. Shall I proceed?")
    upload = endpoints["coding-endpoint-multipart"]["turns"][0]
    assert not runner.evaluate(upload, "What is the multipart file-part field name?")
    assert runner.evaluate(upload, "What JSON fields should the request include?")


def test_self_contained_coding_checks_reject_worker_history_searches():
    spec = {"trace": {"min_subagents": 0, "no_history_search": True}}
    trace = {"reads": [], "tasks": [], "tools": [{"name": "view", "parent": "reviewer"}]}
    assert runner.evaluate_trace(spec, trace) == []
    trace["tools"].append({"name": "functions.session_store_sql", "parent": "reviewer"})
    assert runner.evaluate_trace(spec, trace) == [
        "unnecessary session-history search in a self-contained task",
    ]


def test_single_turn_runs_record_distinct_session_ids(monkeypatch, tmp_path):
    sessions = []

    def ask(sc, model, *, session_id):
        sessions.append(session_id)
        return {"answer": "Ready.", "reads": [], "tasks": []}

    monkeypatch.setattr(runner, "ask", ask)
    runner.run_one({"id": "profile", "prompt": "Hi"}, 2, None, tmp_path)
    assert sessions[0] != sessions[1]
    for number, session_id in enumerate(sessions, 1):
        assert str(runner.uuid.UUID(session_id)) == session_id
        assert f"Session: {session_id}" in (tmp_path / f"profile-run-{number}.md").read_text()


def test_worker_models_are_observed_not_inferred_from_coordinator():
    events = [
        {"type": "subagent.started", "data": {"model": "gpt-5.4-mini", "toolCallId": "coder",
                                             "agentName": "general-purpose"}},
        {"type": "subagent.started", "data": {"model": "gpt-6-astra", "toolCallId": "reviewer",
                                             "agentName": "general-purpose"}},
    ]
    trace = runner.parse_trace("\n".join(runner.json.dumps(event) for event in events))
    assert [agent["model"] for agent in trace["agents"]] == ["gpt-5.4-mini", "gpt-6-astra"]
    assert runner.parse_trace("")["agents"] == []


def test_coordinator_model_events_are_recorded_without_inference():
    events = [
        {"type": "session.model_change", "data": {"model": "reported-model"}},
        {"type": "subagent.started", "data": {"model": "worker-model"}},
    ]
    trace = runner.parse_trace("\n".join(runner.json.dumps(event) for event in events))
    assert trace["models"] == [{"event": "session.model_change", "model": "reported-model"}]
    assert runner.parse_trace("")["models"] == []


def test_single_turn_scenarios_remain_supported(monkeypatch):
    monkeypatch.setattr(runner, "ask", lambda *args, **kwargs: {
        "answer": "Ready.", "reads": [], "tasks": [],
    })
    _, results = runner.run_one({"id": "old", "prompt": "Hi", "must": ["Ready"]}, 1, None)
    assert not results[0][0]


def test_progress_is_visible_before_and_after_model_call(monkeypatch, capsys):
    def ask(*args, **kwargs):
        output = capsys.readouterr().out
        assert "START progress run 1/1" in output
        assert "WAIT  progress run 1/1 turn 1/1" in output
        return {"answer": "Ready.", "reads": [], "tasks": []}

    monkeypatch.setattr(runner, "ask", ask)
    runner.run_one({"id": "progress", "prompt": "Hi"}, 1, None)
    output = capsys.readouterr().out
    assert "PASS  progress run 1/1 turn 1/1" in output
    assert "DONE  progress run 1/1: PASS" in output


def test_transcripts_saved_incrementally_even_on_later_failure(monkeypatch, tmp_path):
    calls = []

    def ask(*args, **kwargs):
        calls.append(1)
        log = (tmp_path / "recorded-run-1.md").read_text()
        if len(calls) == 1:
            assert "First question" in log
            return {"answer": "First answer", "reads": [], "tasks": []}
        assert "First answer" in log
        assert "Second question" in log
        raise RuntimeError("synthetic failure")

    monkeypatch.setattr(runner, "ask", ask)
    runner.run_one({"id": "recorded", "turns": [
        {"prompt": "First question"}, {"prompt": "Second question"},
    ]}, 1, None, tmp_path)
    text = (tmp_path / "recorded-run-1.md").read_text()
    assert "First answer" in text
    assert "**ERROR:** synthetic failure" in text
    assert "## Result: FAIL" in text


def test_successful_transcripts_are_also_saved(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "ask", lambda *args, **kwargs: {
        "answer": "Recorded answer", "reads": [], "tasks": [],
    })
    runner.run_one({"id": "success", "prompt": "Question"}, 2, None, tmp_path)
    for number in (1, 2):
        text = (tmp_path / f"success-run-{number}.md").read_text()
        assert "Question" in text and "Recorded answer" in text
        assert "## Result: PASS" in text


def test_fixture_evidence_is_saved_without_another_model_call(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "ask", lambda *args, **kwargs: {
        "answer": "Done.", "reads": [], "tasks": [],
        "build_result": {"returncode": 0, "output": ""},
        "artifact_files": {"fixture.kt": "val example = 1"},
    })
    runner.run_one({"id": "fixture", "prompt": "Change"}, 1, None, tmp_path)
    text = (tmp_path / "fixture-run-1.md").read_text()
    assert "Independent fixture check: `./mvnw -q test detekt:check`, exit 0" in text
    assert "#### fixture.kt" in text and "val example = 1" in text


def test_failed_process_check_keeps_delegation_evidence(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "ask", lambda *args, **kwargs: {
        "answer": "Done.", "reads": [], "tasks": ["Review this; return VERDICT: PASS/FAIL."],
    })
    runner.run_one({"id": "missing-rules", "prompt": "Change",
                    "trace": {"rules_in_reviewer": True}}, 1, None, tmp_path)
    text = (tmp_path / "missing-rules-run-1.md").read_text()
    assert "the reviewer task does not carry full rules.md" in text
    assert "Review this; return VERDICT: PASS/FAIL." in text


def test_rules_require_every_rule_in_both_tasks():
    rules = runner.source_body(runner.TEMPLATE / ".github/skills/perf-coding/rules.md")
    sc = {"agent": "perf-coding", "trace": {"rules_in_task": True, "rules_in_reviewer": True}}
    trace = {"reads": [], "tasks": [rules, "VERDICT: PASS/FAIL\n" + rules]}
    assert runner.evaluate_trace(sc, trace) == []
    trace["tasks"][1] = "VERDICT: PASS/FAIL. Never read or print .env."
    assert len(runner.evaluate_trace(sc, trace)) == 2
    trace["tasks"] = ["Never read or print", "VERDICT\n" + rules]
    assert runner.evaluate_trace(sc, trace) == [
        "full rules.md body is not embedded in every sub-agent task"]


def test_tool_ownership_separates_orchestrator_from_workers():
    events = [
        {"type": "tool.execution_start", "data": {"toolName": "task", "arguments": {"prompt": "Implement"}}},
        {"type": "tool.execution_start", "data": {"toolName": "bash", "parentToolCallId": "worker", "arguments": {}}},
        {"type": "tool.execution_start", "data": {"toolName": "bash", "arguments": {}}},
        {"type": "tool.execution_start", "data": {"toolName": "task", "parentToolCallId": "worker",
                                                "arguments": {"prompt": "Nested"}}},
    ]
    trace = runner.parse_trace("\n".join(runner.json.dumps(e) for e in events))
    assert trace["tasks"] == ["Implement"]
    assert runner.evaluate_trace({"trace": {"orchestrator_read_only": True}}, trace) == [
        "orchestrator directly called bash"]


def test_freeform_patch_arguments_do_not_break_tool_ownership():
    events = [
        {"type": "tool.execution_start", "data": {"toolName": "apply_patch",
         "arguments": "*** Begin Patch\n*** End Patch", "parentToolCallId": "coder"}},
        {"type": "tool.execution_start", "data": {"toolName": "apply_patch",
         "arguments": "*** Begin Patch\n*** End Patch"}},
    ]
    trace = runner.parse_trace("\n".join(runner.json.dumps(event) for event in events))
    assert trace["tools"] == [{"name": "apply_patch", "parent": "coder"},
                              {"name": "apply_patch", "parent": None}]
    spec = {"trace": {"min_subagents": 0, "orchestrator_read_only": True, "allow_task_state": True}}
    assert runner.evaluate_trace(spec, trace) == ["orchestrator directly called apply_patch"]


@pytest.mark.parametrize("command", [
    "python .github/scripts/task_state.py show items-summary",
    "python3 ./.github/scripts/task_state.py init items-summary --data '{\"goal\":\"summary\", \"intent\":\"interview\"}'",
    "python .github/scripts/task_state.py patch items-summary --revision 2 --data "
    "'{\"detail.total\":{\"value\":\"$.total\", \"source\":\"user\"}}'",
    "python3 .github/scripts/task_state.py validate-report items-summary --revision 5 --data "
    "'{\"role\":\"reviewer\"}'",
])
def test_coordinator_may_only_use_explicitly_enabled_state_helper(command):
    event = {"type": "tool.execution_start", "data": {"toolName": "bash", "arguments": {"command": command}}}
    trace = runner.parse_trace(runner.json.dumps(event))
    assert trace["tools"][0]["command"] == command
    spec = {"agent": "perf-coding", "trace": {"min_subagents": 0, "orchestrator_read_only": True,
                                            "allow_task_state": True}}
    assert not runner.evaluate_trace(spec, trace)
    spec["trace"]["allow_task_state"] = False
    assert runner.evaluate_trace(spec, trace) == ["orchestrator directly called bash"]
    spec["trace"]["allow_task_state"] = True
    spec["agent"] = "perf-orchestrator"
    assert runner.evaluate_trace(spec, trace) == ["orchestrator directly called bash"]


@pytest.mark.parametrize("command", [
    "./mvnw -q test",
    "python other.py show task",
    "python .github/scripts/task_state.py show task && echo unrelated",
    "python .github/scripts/task_state.py show task; echo unrelated",
    "python .github/scripts/task_state.py show task > output.json",
    "python .github/scripts/task_state.py show task | cat",
    "python .github/scripts/task_state.py show task --revision 1",
    "python .github/scripts/task_state.py patch task --data '{}' --revision 0",
    "python .github/scripts/task_state.py init task --data \"$(echo '{}')\"",
    "python .github/scripts/task_state.py init task --data \"$PAYLOAD\"",
    "python .github/scripts/task_state.py show ../task",
])
def test_state_exception_does_not_allow_general_shell_execution(command):
    assert not runner.is_task_state_command(command)


def test_coding_implementation_fixtures_require_persisted_acceptance():
    scenarios = runner.json.loads(runner.SCENARIOS.read_text())
    implementation = [sc for sc in scenarios if sc["id"] in {
        "coding-agent-adds-domain-end-to-end", "coding-agent-extends-domain-end-to-end"}]
    assert len(implementation) == 2
    for sc in implementation:
        assert sc["trace"]["allow_task_state"] and sc["trace"]["verify_task_state"]
        assert ".github/scripts/task_state.py" in sc["trace"]["unchanged_files"]
    new = next(sc for sc in implementation if sc["id"] == "coding-agent-adds-domain-end-to-end")
    existing = next(sc for sc in implementation if sc["id"] == "coding-agent-extends-domain-end-to-end")
    assert not new.get("demo")
    assert "src/main/kotlin/cz/example/perf/domain/items" in new["trace"]["files_absent"]
    assert existing["demo"]


def test_closed_mock_reserves_a_non_listening_loopback_port(monkeypatch):
    from urllib.parse import urlparse
    def run(cmd, **kwargs):
        if cmd[0] == "copilot":
            prompt = cmd[cmd.index("-p") + 1]
            assert "__MOCK_URL__" not in prompt
            url = urlparse(prompt)
            assert url.hostname == "127.0.0.1"
            with runner.socket.socket() as sock:
                sock.settimeout(1)
                assert sock.connect_ex((url.hostname, url.port)) != 0
            return runner.subprocess.CompletedProcess(
                cmd, 0, '{"type":"assistant.message","data":{"content":"Refused."}}\n', "")
        return runner.subprocess.CompletedProcess(cmd, 0, "", "")
    monkeypatch.setattr(runner.subprocess, "run", run)
    monkeypatch.setattr(runner, "run_copilot", run)
    trace = runner.ask({"prompt": "__MOCK_URL__", "workdir": "scaffold", "closed_mock": True}, None)
    assert trace["mock_url"].startswith("http://127.0.0.1:")


def test_cli_output_is_saved_and_nonzero_exit_remains_visible(tmp_path):
    prefix = tmp_path / "process"
    result = runner.run_copilot(
        [runner.sys.executable, "-c",
         "import sys; print('partial event', flush=True); print('failure', file=sys.stderr); sys.exit(7)"],
        cwd=tmp_path, timeout=5, output_prefix=prefix,
    )
    assert result.returncode == 7
    assert result.stdout.strip() == "partial event"
    assert result.stderr.strip() == "failure"
    assert Path(f"{prefix}.stdout.jsonl").read_text() == result.stdout
    assert Path(f"{prefix}.stderr.log").read_text() == result.stderr


@pytest.mark.skipif(runner.os.name != "posix", reason="POSIX process-group regression")
def test_timeout_stops_descendants_and_preserves_streamed_output(tmp_path):
    child = (
        "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        "print('child-ready',flush=True); time.sleep(30)"
    )
    parent = (
        "import subprocess,sys,time; "
        f"p=subprocess.Popen([sys.executable,'-c',{child!r}]); "
        "print('child-pid='+str(p.pid),flush=True); time.sleep(30)"
    )
    prefix = tmp_path / "timeout"
    started = runner.time.monotonic()
    with pytest.raises(RuntimeError, match="timed out.*process tree stopped"):
        runner.run_copilot([runner.sys.executable, "-c", parent], cwd=tmp_path,
                           timeout=0.5, output_prefix=prefix)
    assert runner.time.monotonic() - started < 5
    output = Path(f"{prefix}.stdout.jsonl").read_text()
    assert "child-ready" in output
    pid = next(line.split("=")[1] for line in output.splitlines() if line.startswith("child-pid="))
    state = runner.subprocess.run(["ps", "-p", pid, "-o", "stat="], capture_output=True, text=True).stdout.strip()
    assert not state or state.startswith("Z"), f"descendant still running: {state}"


def test_model_calls_get_per_turn_stream_paths_and_timeout(monkeypatch, tmp_path):
    calls = []

    def ask(sc, *args, **kwargs):
        calls.append(sc)
        return {"answer": "Ready.", "reads": [], "tasks": []}

    monkeypatch.setattr(runner, "ask", ask)
    runner.run_one({"id": "bounded", "_timeout": 42, "_cli_version": "test-version",
                    "turns": [{"prompt": "First"}, {"prompt": "Second"}]}, 1, None, tmp_path)
    assert all(call["_timeout"] == 42 for call in calls)
    assert calls[0]["_output_prefix"] != calls[1]["_output_prefix"]
    text = (tmp_path / "bounded-run-1.md").read_text()
    assert "CLI version: test-version" in text
    assert "not pinned" in text and "empty means unreported" in text


def test_cli_stage_uses_actual_event_not_stream_content(tmp_path):
    stream = tmp_path / "events.jsonl"
    stream.write_text(
        '{"type":"model.call_start","data":{"model":"observed"}}\n'
        '{"type":"assistant.tool_call_delta","data":{"inputDelta":"incomplete"}}\n'
        '{"unfinished":'
    )
    assert runner.cli_stage(stream) == "model.call_start observed"
    stream.write_text(
        '{"type":"agent.interrupted","data":{"activity":"model_call","cancelPhase":"pre_first_token"}}\n'
    )
    assert runner.cli_stage(stream) == "agent.interrupted model_call (pre_first_token)"


@pytest.mark.skipif(runner.os.name != "posix", reason="POSIX cancellation regression")
def test_parallel_run_cancellation_stops_active_cli_and_skips_next_run(tmp_path):
    from threading import Timer

    cancel = runner.Event()
    timer = Timer(0.3, cancel.set)
    timer.start()
    try:
        with pytest.raises(RuntimeError, match="cancelled; launched process tree stopped"):
            runner.run_copilot(
                [runner.sys.executable, "-c", "import time; print('started',flush=True); time.sleep(30)"],
                cwd=tmp_path, timeout=30, output_prefix=tmp_path / "cancel", cancel_event=cancel,
            )
    finally:
        timer.join()
    _, results = runner.run_one({"id": "cancelled", "_cancel": cancel}, 2, None)
    assert results == [(["cancelled before starting next run"], "")]


@pytest.mark.skipif(runner.os.name != "posix", reason="POSIX SIGINT integration")
def test_ctrl_c_cancels_thread_pool_without_waiting_for_model_timeout(tmp_path):
    from threading import Timer

    marker = tmp_path / "cli.pid"
    fake_cli = tmp_path / "copilot"
    fake_cli.write_text(
        f"#!{runner.sys.executable}\n"
        "import os,sys,time\nfrom pathlib import Path\n"
        "if '--version' in sys.argv:\n    print('test-cli-version')\nelse:\n"
        f"    Path({str(marker)!r}).write_text(str(os.getpid()))\n"
        "    print('{\"type\":\"model.call_start\",\"data\":{\"model\":\"fake\"}}',flush=True)\n"
        "    time.sleep(30)\n"
    )
    fake_cli.chmod(0o755)
    process = runner.subprocess.Popen(
        [runner.sys.executable, str(TESTS / "run_scenarios.py"),
         "--only", "coding-endpoint-get-query", "--runs", "2", "--timeout", "30",
         "--log-dir", str(tmp_path / "logs")],
        stdout=runner.subprocess.PIPE, stderr=runner.subprocess.PIPE, text=True,
        env={**runner.os.environ, "PATH": str(tmp_path) + runner.os.pathsep + runner.os.environ["PATH"]},
    )
    timer = Timer(1.5, lambda: process.send_signal(runner.signal.SIGINT))
    timer.start()
    try:
        stdout, stderr = process.communicate(timeout=8)
    finally:
        timer.cancel()
        timer.join()
        if process.poll() is None:
            process.kill()
            process.wait()
    assert process.returncode == 130, stdout + stderr
    assert "active CLI processes stopped" in stderr
    assert marker.exists(), "fixture CLI did not start before interruption"
    state = runner.subprocess.run(
        ["ps", "-p", marker.read_text(), "-o", "stat="], capture_output=True, text=True,
    ).stdout.strip()
    assert not state or state.startswith("Z"), f"fixture CLI still running: {state}"


def test_regression_prompts_do_not_prescribe_the_answer():
    scenarios = {sc["id"]: sc for sc in runner.json.loads(runner.SCENARIOS.read_text())}
    for name in ("coding-unknown-existing-domain", "coding-domain-collision",
                 "coding-endpoint-get-query", "coding-endpoint-unknown-content-type"):
        prompt = scenarios[name]["prompt"]
        assert "end with one direct question" not in prompt
        assert "Explicitly name the GET method" not in prompt
        assert "explicitly say you will not assume JSON" not in prompt
    content = scenarios["coding-endpoint-unknown-content-type"]
    assert not runner.evaluate(content, "I won't assume JSON. What exact Content-Type and sanitized sample apply?")
    assert runner.evaluate(content, "Use JSON. What Content-Type and sanitized sample apply?")


def test_interactive_completion_requires_final_message_and_matching_turn_end():
    message = {"type": "assistant.message", "data": {"turnId": "final", "content": "Which domain?"}}
    end = {"type": "assistant.turn_end", "data": {"turnId": "final"}}
    assert runner.interactive_turn_finished([message, end])
    assert not runner.interactive_turn_finished([message])
    assert not runner.interactive_turn_finished([message, {"type": "assistant.turn_end", "data": {"turnId": "other"}}])
    tool_message = {"type": "assistant.message", "data": {
        "turnId": "final", "content": "Reading.", "toolRequests": [{"name": "view"}],
    }}
    assert not runner.interactive_turn_finished([tool_message, end])


def test_native_question_is_part_of_user_visible_response_without_inventing_an_answer():
    events = [
        {"type": "assistant.message", "data": {"content": "The domain is missing."}},
        {"type": "tool.execution_start", "data": {"toolName": "ask_user", "arguments": {
            "question": "Which existing domain should receive GET /reports?",
        }}},
    ]
    trace = runner.parse_trace("\n".join(runner.json.dumps(event) for event in events))
    assert trace["questions"] == ["Which existing domain should receive GET /reports?"]
    assert not runner.evaluate({"requires_input": True, "max_questions": 1}, trace["answer"])
    assert "The domain is missing." in trace["answer"]


def test_missing_domain_regression_uses_actual_interactive_mode():
    scenarios = {sc["id"]: sc for sc in runner.json.loads(runner.SCENARIOS.read_text())}
    assert scenarios["coding-unknown-existing-domain"]["interactive_cli"]


def test_resumed_interview_only_exposes_new_turn_events(tmp_path):
    events = tmp_path / "events.jsonl"
    old = '{"type":"assistant.message","data":{"content":"Old question?"}}\n'
    events.write_text(old)
    offset = events.stat().st_size
    new = '{"type":"assistant.message","data":{"content":"New question?"}}\n'
    with events.open("a") as stream:
        stream.write(new)
    assert runner.interactive_events_since(events, offset) == new
    assert runner.parse_trace(runner.interactive_events_since(events, offset))["answer"] == "New question?"


def test_native_multiturn_resumes_same_session_and_uses_text_questions(monkeypatch):
    calls = []

    def run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return runner.subprocess.CompletedProcess(
            cmd, 0, '{"type":"assistant.message","data":{"content":"Next question?"}}\n', "")

    monkeypatch.setattr(runner, "run_interactive_copilot", run)
    scenario = {"id": "native", "workdir": "template", "interactive_cli": True,
                "turns": [{"prompt": "First"}, {"prompt": "Second"}]}
    _, result = runner.run_one(scenario, 2, None)
    assert all(not errors for errors, _ in result)
    assert [kwargs["resume"] for _, kwargs in calls] == [False, True, False, True]
    assert all("ask_user" not in cmd for cmd, _ in calls)
    sessions = [cmd[cmd.index("--session-id") + 1] for cmd, _ in calls]
    assert sessions[0] == sessions[1] and sessions[2] == sessions[3]
    assert sessions[0] != sessions[2]


def test_native_multiturn_catalog_keeps_correction_and_decline_gates():
    scenarios = {sc["id"]: sc for sc in runner.json.loads(runner.SCENARIOS.read_text())}
    for name in ("coding-interactive-new-domain", "coding-interactive-existing-domain",
                 "coding-endpoint-json-patch-intake"):
        sc = scenarios[name]
        assert sc["interactive_cli"] and sc["workdir"] == "template"
        assert sc["turns"][-2]["requires_input"]
        assert "No" in sc["turns"][-1]["prompt"]
        assert not sc["trace"]["max_subagents"]


def test_status_correction_allows_explicit_rejection_of_old_status():
    scenarios = {sc["id"]: sc for sc in runner.json.loads(runner.SCENARIOS.read_text())}
    correction = scenarios["coding-interactive-new-domain"]["turns"][-2]
    assert not runner.evaluate(correction, "GET /orders will expect **204**, not 200. Shall I implement?")
    for answer in ("Expect 200. Updated to 204. Shall I implement?",
                   "Expected status is **200**, or 204. Shall I implement?",
                   "Expecting `200`, with 204 elsewhere. Shall I implement?"):
        assert runner.evaluate(correction, answer)


def test_parallel_native_interviews_fail_before_cli_or_model_calls(monkeypatch, capsys):
    monkeypatch.setattr(runner.sys, "argv", ["run_scenarios.py", "--only",
                                           "coding-endpoint-json-patch-intake", "-j", "2"])
    monkeypatch.setattr(runner.shutil, "which", lambda *args: pytest.fail("CLI discovery was reached"))
    with pytest.raises(SystemExit, match="2"):
        runner.main()
    assert "native interactive scenarios require -j 1" in capsys.readouterr().err


@pytest.mark.skipif(runner.os.name != "posix", reason="POSIX process-group cleanup")
@pytest.mark.parametrize("state", ["S", "Z", None])
def test_cleanup_permission_error_is_only_tolerated_for_a_verified_stopped_group(monkeypatch, state):
    class Process:
        pid = 12345

        def wait(self, timeout):
            return 0

    signals = []

    def killpg(pid, sig):
        signals.append((pid, sig))
        if sig == runner.signal.SIGKILL:
            raise PermissionError("group cleanup")

    def run(command, **kwargs):
        assert command == ["ps", "-axo", "pgid=,stat="]
        assert kwargs["check"]
        return runner.subprocess.CompletedProcess(command, 0, f"12345 {state}\n" if state else "", "")

    monkeypatch.setattr(runner.os, "killpg", killpg)
    monkeypatch.setattr(runner.subprocess, "run", run)
    if state == "S":
        with pytest.raises(PermissionError):
            runner.stop_process_tree(Process())
    else:
        runner.stop_process_tree(Process())
    assert signals == [(12345, runner.signal.SIGTERM), (12345, runner.signal.SIGKILL)]


@pytest.mark.skipif(runner.sys.platform != "darwin", reason="Darwin zombie-group signaling")
def test_darwin_zombie_group_is_already_stopped(tmp_path):
    process = runner.subprocess.Popen(
        [runner.sys.executable, "-c", "import time; time.sleep(30)"],
        cwd=tmp_path, start_new_session=True,
    )
    try:
        runner.os.killpg(process.pid, runner.signal.SIGTERM)
        deadline = runner.time.monotonic() + 5
        while True:
            state = runner.subprocess.run(["ps", "-p", str(process.pid), "-o", "stat="],
                                          capture_output=True, text=True, check=True).stdout.strip()
            if state.startswith("Z"):
                break
            assert runner.time.monotonic() < deadline
            runner.time.sleep(0.02)
        runner.stop_process_tree(process)
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)


@pytest.mark.skipif(runner.os.name != "posix", reason="POSIX pseudo-terminal integration")
@pytest.mark.parametrize("resume", [False, True])
def test_native_completed_turn_exits_gracefully_and_does_not_replay_old_events(tmp_path, monkeypatch, resume):
    session = tmp_path / ".copilot/session-state/native-test"
    session.mkdir(parents=True)
    events, marker = session / "events.jsonl", tmp_path / "exited"
    if resume:
        events.write_text('{"type":"assistant.message","data":{"content":"Old question?"}}\n')
    fake = tmp_path / "fake_cli.py"
    new_events = (
        '{"type":"assistant.message","data":{"turnId":"new","content":"New question?"}}\n'
        '{"type":"assistant.turn_end","data":{"turnId":"new"}}\n'
    )
    fake.write_text(
        "import sys\nfrom pathlib import Path\n"
        f"with Path({str(events)!r}).open('a') as stream:\n    stream.write({new_events!r})\n"
        "line = sys.stdin.readline()\n"
        "assert line.strip() == '/exit', repr(line)\n"
        f"Path({str(marker)!r}).write_text('graceful')\n"
    )
    monkeypatch.setattr(runner.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(runner, "stop_process_tree",
                        lambda *args: pytest.fail("completed native turn was force-stopped"))
    result = runner.run_interactive_copilot(
        [runner.sys.executable, str(fake), "-p", "Prompt", "--session-id", "native-test",
         "--output-format", "json"], cwd=tmp_path, timeout=10,
        output_prefix=tmp_path / "result", resume=resume,
    )
    assert marker.read_text() == "graceful"
    assert result.stdout == new_events
    assert Path(f"{tmp_path / 'result'}.stdout.jsonl").read_text() == new_events

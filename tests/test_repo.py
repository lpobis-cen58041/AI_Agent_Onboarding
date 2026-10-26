"""Deterministic checks of the perf-setup agent repo (no model, no network, nothing is submitted)."""
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".github" / "scripts"
SKILL = ROOT / ".github" / "skills" / "perf-setup"
AGENTS_DIR = ROOT / ".github" / "agents"
AGENT = AGENTS_DIR / "perf-orchestrator.agent.md"
ALL_AGENTS = sorted(AGENTS_DIR.glob("*.agent.md"))
TEMPLATE = SKILL / "template"


def run(*args, cwd=SCRIPTS, env=None):
    import os
    e = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    e.update(env or {})
    return subprocess.run([sys.executable, *args], cwd=cwd, capture_output=True, text=True, env=e, timeout=300)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ---- configuration files ----------------------------------------------------------------

@pytest.mark.parametrize("name", ["access.json", "sources.json", "tickets.json"])
def test_config_is_valid_json(name):
    assert isinstance(load(SKILL / name), dict)


def test_access_groups_have_domain_and_both_envs():
    cfg = load(SKILL / "access.json")
    for env in ("prod", "test"):
        assert cfg["groups"][env], env
        assert cfg["portals"][env].startswith("https://")
        for g in cfg["groups"][env]:
            assert re.fullmatch(r"[A-Z]+\\[A-Za-z0-9_]+", g), f"bad group name: {g}"
    assert cfg["groups"] == {
        "prod": ["XUC\\APIMAN_DEVELOPER"],
        "test": ["CSINT\\Alfred_Authentication_Users", "CSINT\\Alfred_Performance_Testing"],
    }
    assert "CSIN\\GHB_DEV_GEORGEPETE_WRITE" in cfg["georgepete_only_groups"]["prod"]
    assert not set(sum(cfg["groups"].values(), [])) & set(
        sum(cfg["georgepete_only_groups"].values(), [])
    )


def test_sources_reference_unique_files():
    cfg = load(SKILL / "sources.json")
    files = [p["file"] for p in cfg["extra_pages"]]
    assert len(files) == len(set(files))
    assert all(isinstance(p["id"], int) for p in cfg["extra_pages"])
    assert all(isinstance(t["root_id"], int) for t in cfg["trees"])


def test_tickets_entries_complete():
    for item in load(SKILL / "tickets.json")["required"]:
        assert item["name"] and item["how"]
    assert all("Redim access" not in item["name"] for item in load(SKILL / "tickets.json")["required"])


def test_glossary_covers_key_terms():
    text = (SKILL / "glossary.md").read_text(encoding="utf-8")
    for term in ("RPS", "PETE", "Redim", "Feeder", "Artifactory", "ServiceNow"):
        assert term in text


def test_general_load_testing_guidance_excludes_project_details():
    guidance = (PLAYBOOKS / "load-testing-basics.md").read_text(encoding="utf-8")
    knowledge = (PLAYBOOKS / "knowledge.md").read_text(encoding="utf-8")
    for project_detail in ("GEORGEPETE", "George - PERF testy na PROD", "DAF-332673",
                           r"CSIN\GHB_DEV_GEORGEPETE_WRITE"):
        assert project_detail not in guidance
    assert "load-testing-basics.md" in knowledge
    assert "Do not consult or reproduce the source project's page" in knowledge
    assert "Production testing requires explicit approval" in guidance


# ---- agent definition -------------------------------------------------------------------

def test_agent_frontmatter():
    import yaml
    text = AGENT.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert m, "missing frontmatter"
    data = yaml.safe_load(m.group(1))
    assert data["name"] == "perf-orchestrator"
    assert data["model"] == "GPT-6 Astra"
    assert "execute" in data["tools"]


def test_agent_references_existing_scripts_and_files():
    text = "\n".join(f.read_text(encoding="utf-8") for f in ALL_AGENTS)
    for script in set(re.findall(r"`?(?:python )?([a-z_]+\.py)\b", text)):
        assert (SCRIPTS / script).exists(), f"agent mentions missing script {script}"
    for f in ("access.json", "tickets.json", "sources.json", "glossary.md"):
        if f in text:
            assert (SKILL / f).exists()


def test_agent_safety_rules_present():
    text = AGENT.read_text(encoding="utf-8")
    assert "Never read or print the content of `.env`" in text
    assert "Invent nothing" in text
    assert "does NOT submit access requests" in text         # no autonomous request submission
    assert "explicit confirmation" in text
    assert "Never commit secrets" in text


def test_agent_has_no_embedded_secrets():
    text = AGENT.read_text(encoding="utf-8")
    assert not re.search(r"(?i)(token|password|key)\s*=\s*[A-Za-z0-9+/_-]{16,}", text)


# ---- repository hygiene -----------------------------------------------------------------

def tracked_files():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    if out.returncode != 0:
        pytest.skip("not a git checkout")
    return out.stdout.splitlines()


def test_no_secrets_or_snapshots_tracked():
    files = tracked_files()
    assert ".env" not in files
    assert not any(f.startswith(".github/skills/perf-setup/wiki/") for f in files)
    assert ".github/skills/perf-setup/manifest.json" not in files
    assert not any(f.endswith("secrets.txt") for f in files)


def test_gitignore_covers_sensitive_paths():
    text = (ROOT / ".gitignore").read_text()
    for entry in (".env", ".github/skills/perf-setup/wiki/", ".github/skills/perf-setup/manifest.json"):
        assert entry in text


def test_tracked_text_has_no_token_patterns():
    pat = re.compile(r"(gh[pousr]_[A-Za-z0-9]{30,}|BEGIN (RSA |OPENSSH )?PRIVATE KEY|Bearer [A-Za-z0-9._-]{30,})")
    for f in tracked_files():
        p = ROOT / f
        if p.suffix in {".py", ".md", ".json", ".yml", ".kt", ".xml", ".example", ".csv", ".properties"} and p.is_file():
            assert not pat.search(p.read_text(encoding="utf-8", errors="ignore")), f"possible secret in {f}"


def test_env_example_has_no_values_for_secrets():
    for line in (ROOT / ".env.example").read_text().splitlines():
        if re.match(r"(?:\w*(TOKEN|KEY|PASSWORD|COOKIE)\w*)=", line):
            assert line.split("=", 1)[1].strip() == "", f"secret value in .env.example: {line}"


# ---- scripts ----------------------------------------------------------------------------

@pytest.mark.parametrize("script", sorted(p.name for p in SCRIPTS.glob("*.py")))
def test_scripts_compile(script):
    r = run("-m", "py_compile", script)
    assert r.returncode == 0, r.stderr


def test_scripts_match_supported_workflow():
    assert {p.name for p in SCRIPTS.glob("*.py")} == {
        "wiki.py", "sync_wiki_pages.py", "crawl_confluence.py", "check_env.py", "scaffold.py",
        "install_coding_agent.py",
    }
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "playwright" not in requirements
    assert "api" not in load(SKILL / "access.json")
    assert not {822847120, 140673376} & {
        page["id"] for page in load(SKILL / "sources.json")["extra_pages"]
    }


# ---- sample template + scaffold ---------------------------------------------------------

def test_template_env_files_have_identical_keys():
    def keys(f):
        return {l.split("=", 1)[0] for l in (TEMPLATE / "src/main/resources/env" / f).read_text().splitlines()
                if l.strip() and not l.startswith("#")}
    assert keys("test.properties") == keys("prod.properties")


def test_template_ci_rows_point_to_existing_simulations():
    rows = (TEMPLATE / "ci/simulation-data.csv").read_text().splitlines()[1:]
    assert rows
    for row in rows:
        cls = row.split(",")[0]
        path = TEMPLATE / "src/main/kotlin" / (cls.replace(".", "/") + ".kt")
        assert path.exists(), f"{cls} has no file {path}"


def test_template_follows_domain_layout():
    base = TEMPLATE / "src/main/kotlin/cz/example/perf"
    for domain in (base / "domain").iterdir():
        for layer in ("requests", "steps", "flows", "usecases", "data"):
            assert (domain / layer).is_dir(), f"{domain.name} lacks {layer}"
        assert (base / "simulations/domain" / domain.name).is_dir()


def test_template_has_no_internal_hosts():
    pat = re.compile(r"(csin\.cz|csint\.cz|csas\.cz|csast\.|artifactory\.csin)")
    for p in TEMPLATE.rglob("*"):
        if p.is_file() and p.suffix in {".kt", ".xml", ".md", ".yml", ".csv", ".properties"}:
            assert not pat.search(p.read_text(encoding="utf-8", errors="ignore")), f"internal host in {p}"


def test_scaffold_creates_repo(tmp_path):
    r = run("scaffold.py", "perf-sample-test", "--dest", str(tmp_path), "--no-test", "--no-git")
    assert r.returncode == 0, r.stderr
    out = tmp_path / "perf-sample-test"
    assert (out / "pom.xml").exists() and (out / "mvnw").exists()
    leftovers = [p for p in out.rglob("*") if p.is_file() and p.suffix in {".xml", ".md", ".yml", ".kt"}
                 and "__PROJECT_NAME__" in p.read_text(encoding="utf-8", errors="ignore")]
    assert not leftovers
    assert run("scaffold.py", "perf-sample-test", "--dest", str(tmp_path), "--no-test", "--no-git").returncode != 0
    assert run("scaffold.py", "Bad Name", "--dest", str(tmp_path)).returncode != 0


# ---- new_domain.py + coding guide --------------------------------------------------------

def _scaffolded(tmp_path, *, demo=False):
    assert run("scaffold.py", "nd", "--dest", str(tmp_path), "--no-test", "--no-git",
               *(["--demo"] if demo else [])).returncode == 0
    return tmp_path / "nd"


def test_default_scaffold_has_infrastructure_but_no_domain_or_demo_wiring(tmp_path):
    repo = _scaffolded(tmp_path)
    base = repo / "src/main/kotlin/cz/example/perf"
    assert not (base / "domain").exists()
    assert not (base / "simulations/domain").exists()
    for relative in ("src/test/resources/items", "src/test/kotlin/cz/example/perf/contract",
                     "src/test/kotlin/cz/example/perf/setup/WeightSumTest.kt",
                     ".github/scripts/check_items_http.py", ".github/workflows/DemoHttp.yml"):
        assert not (repo / relative).exists(), relative
    assert (base / "setup/UseCase.kt").is_file()
    assert (repo / "src/test/kotlin/cz/example/perf/setup/MixBuilderTest.kt").is_file()
    assert (repo / "ci/simulation-data.csv").read_text() == "simulation,source,target\n"
    for env in ("test", "prod"):
        assert all(not line.strip() or line.startswith("#") for line in
                   (repo / f"src/main/resources/env/{env}.properties").read_text().splitlines())
    for path in (repo / "src").rglob("*"):
        if path.is_file() and path.suffix in {".kt", ".csv", ".properties"}:
            assert "Items" not in path.read_text(), path
            assert "itemsList" not in path.read_text(), path


def test_explicit_demo_preserves_example_code_tests_and_ci(tmp_path):
    repo = _scaffolded(tmp_path, demo=True)
    for relative in ("src/main/kotlin/cz/example/perf/domain/items/requests/ItemsRequests.kt",
                     "src/main/kotlin/cz/example/perf/simulations/domain/items/ItemsMixSimulation.kt",
                     "src/test/kotlin/cz/example/perf/setup/WeightSumTest.kt",
                     "src/test/resources/items/items.csv", ".github/scripts/check_items_http.py",
                     "src/main/resources/env/test.properties", "src/main/resources/env/prod.properties",
                     "ci/simulation-data.csv"):
        assert (repo / relative).read_bytes() == (TEMPLATE / relative).read_bytes()
    assert (repo / ".github/workflows/DemoHttp.yml").is_file()


def test_onboarding_defaults_to_new_project_without_a_demo_question():
    agent = AGENT.read_text()
    repo_guide = (SKILL / "playbooks/repo.md").read_text()
    coding_guide = (TEMPLATE / ".github/skills/perf-coding/coding-guide.md").read_text()
    assert "Default to a new project with shared infrastructure and no sample domains" in agent
    assert "Add `--demo` only if the user explicitly requests" in repo_guide
    assert "Do not ask an extra demo-versus-project question" in repo_guide
    assert "Generate only the requested domain, not an items example" in coding_guide


def new_domain(repo, *args):
    """Runs the generator exactly as a user of the scaffolded repo would."""
    return subprocess.run([sys.executable, ".github/scripts/new_domain.py", ".", *args], cwd=repo,
                          capture_output=True, text=True)


def test_scaffold_includes_coding_agent(tmp_path):
    repo = _scaffolded(tmp_path)
    agent = repo / ".github/agents/perf-coding.agent.md"
    assert agent.exists() and "name: perf-coding" in agent.read_text(encoding="utf-8")
    for rel in (".github/skills/perf-coding/rules.md", ".github/skills/perf-coding/coding-guide.md",
                ".github/skills/perf-coding/endpoint-contracts.md", ".github/skills/perf-coding/task-state.md",
                ".github/skills/perf-coding/run-readiness.md", ".github/skills/perf-coding/playbooks/coder.md", ".github/skills/perf-coding/playbooks/reviewer.md",
                ".github/scripts/new_domain.py", ".github/scripts/task_state.py"):
        assert (repo / rel).exists(), rel
    assert ".perf-coding/" in (repo / ".gitignore").read_text()
    state_check = subprocess.run([sys.executable, ".github/scripts/task_state.py", "init", "packaging",
                                  "--data", '{"goal":"Verify packaging","intent":"plan_only"}'],
                                 cwd=repo, capture_output=True, text=True)
    assert state_check.returncode == 0, state_check.stderr
    assert json.loads(state_check.stdout)["phase"] == "on_hold"
    destination = tmp_path / "folder with spaces"
    r = run("scaffold.py", "nd2", "--dest", str(destination), "--no-test", "--no-git")
    assert r.returncode == 0, r.stderr
    command = next(line.removeprefix("Next: ") for line in r.stdout.splitlines() if line.startswith("Next: "))
    assert shlex.split(command) == [
        "cd", str(destination / "nd2"), "&&", "copilot", "--agent", "perf-coding",
        "--model", "gpt-6-astra", "-i", "Start",
    ]


def test_coding_agent_is_self_contained_and_valid(tmp_path):
    import yaml
    repo = _scaffolded(tmp_path)
    text = (repo / ".github/agents/perf-coding.agent.md").read_text(encoding="utf-8")
    data = yaml.safe_load(re.match(r"---\n(.*?)\n---\n", text, re.S).group(1))
    assert data["name"] == "perf-coding" and "agent" in data["tools"]
    assert data["model"] == "GPT-6 Astra"
    assert {"execute", "edit"}.issubset(data["tools"])
    for rel in re.findall(r"`(\.github/[^`*{}<>\s]+?\.(?:md|py))`", text):
        assert (repo / rel).exists(), rel
    for needed in ("at most 3 iterations", "MANDATORY", "task-state.md", "rules.md"):
        assert needed in text, needed
    assert "Never implement requested code yourself" in text
    assert "You coordinate and verify; sub-agents implement." in text
    assert "Use the fewest sub-agent calls" in text
    assert "one coder sub-agent for the whole domain/change" in text
    assert "perf-setup" not in text and "wiki" not in text.lower()
    rules = (repo / ".github/skills/perf-coding/rules.md").read_text(encoding="utf-8")
    assert "Never commit secrets" in rules and "Never run load against TEST/PROD" in rules
    review = (repo / ".github/skills/perf-coding/playbooks/reviewer.md").read_text(encoding="utf-8")
    assert "VERDICT: PASS" in review and "VERDICT: FAIL" in review and "canonical combined" in review
    guide = (repo / ".github/skills/perf-coding/coding-guide.md").read_text(encoding="utf-8")
    assert "new_domain.py" in guide and "UseCasesTest" in guide


def test_coding_guidance_routes_existing_changes_without_regeneration():
    coding = TEMPLATE / ".github/skills/perf-coding"
    agent = (TEMPLATE / ".github/agents/perf-coding.agent.md").read_text(encoding="utf-8")
    guide = (coding / "coding-guide.md").read_text(encoding="utf-8")
    coder = (coding / "playbooks/coder.md").read_text(encoding="utf-8")
    review = (coding / "playbooks/reviewer.md").read_text(encoding="utf-8")
    instructions = (TEMPLATE / ".github/copilot-instructions.md").read_text(encoding="utf-8")
    assert "Use new_domain.py only for a new domain" in guide
    assert "matching" in coder and "coding-guide.md" in coder
    assert "one question per turn" in agent
    assert "A guidance-only request must not run commands or modify files" in agent
    assert "Keep reviewer verdicts internal" in agent
    assert "within 80 words" in agent
    assert "When `ask_user` is available" in agent
    assert "do not also repeat the question in the final answer" in agent
    assert "does not inherit" in agent and "coder's prompt" in agent
    assert "full literal rules.md text, not just a path" in agent
    for task in ("New business domain", "Another endpoint", "New journey", "Change the mix", "Add or fix unit tests"):
        assert task in guide
    for contract in ("both env", "new use case in `all`", "confirm its weight"):
        assert contract in instructions
    assert "exact expected names and weights, not only their sum" in instructions
    assert "not regenerate the domain or add duplicate simulations/rows" in review
    assert "Do not assume every POST returns 200 or 201" in guide
    assert "do not duplicate it in `WeightSumTest`" in guide


def test_coding_guidance_distinguishes_unit_and_runtime_checks():
    coding = TEMPLATE / ".github/skills/perf-coding"
    agent = (TEMPLATE / ".github/agents/perf-coding.agent.md").read_text(encoding="utf-8")
    guide = (coding / "coding-guide.md").read_text(encoding="utf-8")
    rules = (coding / "rules.md").read_text(encoding="utf-8")
    instructions = (TEMPLATE / ".github/copilot-instructions.md").read_text(encoding="utf-8")
    readme = (TEMPLATE / "README.md").read_text(encoding="utf-8")
    assert "HTTP behavior was not exercised" in rules
    assert "constantUsersPerSec" in rules and "not exact HTTP requests per second" in rules
    review = (coding / "playbooks/reviewer.md").read_text(encoding="utf-8")
    assert "Do not require a live endpoint or a mock" in review and "approve a code-only change" in review
    assert "Maven may download dependencies" in instructions
    assert "owned loopback target" in rules and "never authorizes network traffic" in agent
    assert "http://127.0.0.1:8080" in readme
    assert "does not start one for you" in readme


def test_coding_intake_is_progressive_and_skips_known_facts():
    coding = TEMPLATE / ".github/skills/perf-coding"
    agent = (TEMPLATE / ".github/agents/perf-coding.agent.md").read_text(encoding="utf-8")
    guide = (coding / "coding-guide.md").read_text(encoding="utf-8")
    assert "## Interactive intake" in agent
    assert "end the reply with the direct question instead" in agent
    assert "A blocker explanation alone is not intake" in agent
    assert "Distinguish waiting for approval from a plan-only request" in guide
    assert "sole coordinator execution exception" in agent and "task_state.py" in agent
    assert "Source edits, builds, tests, git commands and HTTP commands belong" in agent
    assert "correction must not start implementation" in " ".join(guide.split())
    assert "complete, explicit implementation request already authorizes" in " ".join(agent.split())
    assert "actual existing domains" in guide
    assert "must not also request a new domain name" in guide
    assert "summarize the agreed immediate change in at most 80 words" in guide
    for step in ("**New or existing:**", "**Domain:**", "**Call contract:**",
                 "**Relevant details only:**", "**Journey and mix:**", "**Confirm:**"):
        assert step in guide
    assert "skip everything already supplied or discoverable in the repo" in guide
    assert "An unknown existing domain is not permission to create it" in " ".join(guide.split())
    assert "A request-only change or unit-test change need not alter the mix" in guide


def test_endpoint_intake_separates_profiles_formats_and_http_contracts():
    coding = TEMPLATE / ".github/skills/perf-coding"
    contracts = (coding / "endpoint-contracts.md").read_text(encoding="utf-8")
    guide = (coding / "coding-guide.md").read_text(encoding="utf-8")
    agent = (TEMPLATE / ".github/agents/perf-coding.agent.md").read_text(encoding="utf-8")
    for text in (guide, agent):
        assert "endpoint-contracts.md" in text
        assert "business" in text
    assert "relative endpoint path, then the HTTP method, then the expected" in guide
    for profile in ("Gateway / published API", "Direct public resource",
                    "Authorization-availability check", "Other or unclear API"):
        assert profile in contracts
    for request_format in ("No body", "JSON", "Form URL-encoded", "Multipart / file upload", "Other payload"):
        assert request_format in contracts
    for guard in ("Ask one missing fact per turn", "Skip absent/already supplied fields",
                  "HEAD responses and status 204 have no response body",
                  "Status 202 proves acceptance", "valid transaction-type/risk combinations",
                  "local-mock rules"):
        assert guard in contracts
    assert "real API keys, tokens, identity values" in contracts
    assert "not a global removal of existing headers" in contracts
    assert "task-state.md" in contracts
    assert "GET/POST skeletons only" in guide
    assert "For an explicitly plan-only answer, use at most 120 words" in agent
    for role in ("coder", "reviewer"):
        text = (coding / f"playbooks/{role}.md").read_text(encoding="utf-8")
        assert "endpoint-contract" in text


def test_endpoint_sources_are_explicit_and_not_embedded_in_template():
    sources = {page["id"]: page["file"] for page in load(SKILL / "sources.json")["extra_pages"]}
    assert sources[2134087449] == "02-testovaci-scenare.md"
    assert sources[655922429] == "webapi-architecture.md"
    contracts = (TEMPLATE / ".github/skills/perf-coding/endpoint-contracts.md").read_text(encoding="utf-8")
    for internal in ("cnfl.csin.cz", "zatezove-testy", "GEORGE", "semCLUID"):
        assert internal not in contracts


def test_coding_startup_is_task_focused_and_launch_sends_first_message():
    agent = (TEMPLATE / ".github/agents/perf-coding.agent.md").read_text(encoding="utf-8")
    assert "## Primary purpose and session entry" in agent
    assert 'starts with "Start", "Hi", "Let\'s begin"' in agent
    assert "No repository inspection, baseline checks, delegation or edits" in agent
    assert "For a concrete request, continue with its next missing fact" in agent
    assert "when explicitly requested or when they block the agreed change" in agent
    command = 'copilot --agent perf-coding --model gpt-6-astra -i "Start"'
    for path in (ROOT / "README.md", ROOT / ".github/copilot-instructions.md", AGENT,
                 PLAYBOOKS / "repo.md", TEMPLATE / "README.md",
                 TEMPLATE / ".github/copilot-instructions.md", TEMPLATE / ".github/agents/perf-coding.agent.md"):
        assert command in path.read_text(encoding="utf-8"), path


def test_mock_runs_require_explicit_target_limits_and_review():
    agent = (TEMPLATE / ".github/agents/perf-coding.agent.md").read_text(encoding="utf-8")
    review = (TEMPLATE / ".github/skills/perf-coding/playbooks/reviewer.md").read_text(encoding="utf-8")
    rules = (TEMPLATE / ".github/skills/perf-coding/rules.md").read_text(encoding="utf-8")
    assert 'bare "sure", "yes" or "OK"' in rules
    assert "not a confirmed target" in rules
    assert "wait for explicit permission before creating it or starting a server" in rules
    assert "Run-only tasks need independent review" in rules
    assert "do not probe it" in rules
    assert "no shell chains, pipelines, redirection, arbitrary Python or other scripts" in agent
    assert "without demanding successful execution or retrying the probe" in review


def test_coding_efficiency_preserves_strong_orchestration_checks_and_approval():
    coding = TEMPLATE / ".github/skills/perf-coding"
    agent = (TEMPLATE / ".github/agents/perf-coding.agent.md").read_text(encoding="utf-8")
    coder = (coding / "playbooks/coder.md").read_text(encoding="utf-8")
    reviewer = (coding / "playbooks/reviewer.md").read_text(encoding="utf-8")
    guide = (coding / "coding-guide.md").read_text(encoding="utf-8")
    rules = (coding / "rules.md").read_text(encoding="utf-8")
    commands = (TEMPLATE / ".github/copilot-instructions.md").read_text(encoding="utf-8")
    assert "Keep GPT-6 Astra for orchestration and final acceptance" in agent
    assert "use `gpt-5.4-mini` by default" in agent
    assert "Choose the independent reviewer's model separately" in agent
    assert "Honor explicit user model choices" in agent
    assert "Escalate only a concrete unresolved defect" in agent
    assert "baseline command once before editing" in coder and "combined final command once" in coder
    assert "combined unit/static command yourself once" in reviewer
    assert "Permission waiting is not command execution time" in rules
    assert "do not retry a pending command, bypass approval" in rules
    assert "Do not restate their checklists" in agent
    assert "./mvnw -q test detekt:check" in commands
    for label in ("Baseline evidence", "Change boundary", "Final checks", "Unverified/blockers"):
        assert label in coder
    assert "Do not search session history" in rules
    assert "do not use shell grep/rg/find/cat" in " ".join(reviewer.split())
    assert "Do not recursively scan the repository root" in reviewer
    assert "separate general-purpose worker instructed by the read-only reviewer playbook" in agent
    assert "Reuse existing test helpers" in coder
    assert "Update directly related documentation in the same pass" in coder
    assert "generator `--dry-run`" in coder and "report's `boundary`" in coder
    assert "ordered command strings," in coder and "observed exit codes" in coder
    assert "`generator-preview` and `generator`" in coder
    assert "Include retained generator preview/generation evidence" in agent
    assert "Test actual types/boundaries" in guide
    assert "resolved dependency version" in guide
    assert "not cosmetics or unrelated improvements" in reviewer
    assert "validate-report" in reviewer and "read-only" in reviewer
    assert "schema-only" in agent and "not in a new worker" in agent


def test_coding_rule_ownership_is_explicit_and_compact():
    coding = TEMPLATE / ".github/skills/perf-coding"
    paths = [TEMPLATE / ".github/agents/perf-coding.agent.md", TEMPLATE / ".github/copilot-instructions.md",
             *(coding / rel for rel in ("rules.md", "coding-guide.md", "endpoint-contracts.md",
                                       "task-state.md", "playbooks/coder.md", "playbooks/reviewer.md"))]
    texts = [path.read_text(encoding="utf-8") for path in paths]
    assert sum(len(text.split()) for text in texts) <= 6000
    assert sum("Never read or print the content of `.env`" in text for text in texts) == 1
    assert sum("Permission waiting is not command execution time" in text for text in texts) == 1
    assert "not a technically isolated sandbox" in texts[0]
    assert "task_state.py" in texts[0] and "Do not edit task JSON directly" in texts[0]
    assert "Every mutation after `init`" in texts[5]


def test_scaffold_never_copies_task_approvals_or_runtime_caches(tmp_path, monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location("scaffold_isolation", ROOT / ".github/scripts/scaffold.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    template = tmp_path / "template"
    (template / ".perf-coding/tasks").mkdir(parents=True)
    (template / ".perf-coding/tasks/approved.json").write_text('{"approval":"old"}')
    (template / "__pycache__").mkdir()
    (template / "__pycache__/cached.pyc").write_bytes(b"cache")
    (template / "target/classes").mkdir(parents=True)
    (template / "target/classes/Items.class").write_bytes(b"stale demo build")
    (template / ".git").mkdir()
    (template / ".git/HEAD").write_text("Old template checkout\n")
    (template / "mvnw").write_text("#!/bin/sh\n")
    (template / "README.md").write_text("__PROJECT_NAME__")
    (template / "src/main/resources/env").mkdir(parents=True)
    for env in ("test", "prod"):
        (template / f"src/main/resources/env/{env}.properties").write_text("# Empty\n")
    (template / "ci").mkdir()
    (template / "ci/simulation-data.csv").write_text("simulation,source,target\n")
    monkeypatch.setattr(module, "TEMPLATE", template)
    monkeypatch.setattr(sys, "argv", ["scaffold.py", "fresh", "--dest", str(tmp_path), "--no-test", "--no-git"])
    assert module.main() == 0
    assert not (tmp_path / "fresh/.perf-coding").exists()
    assert not (tmp_path / "fresh/__pycache__").exists()
    assert not (tmp_path / "fresh/target").exists()
    assert not (tmp_path / "fresh/.git").exists()
    assert (tmp_path / "fresh/README.md").read_text() == "fresh"


def test_scaffold_no_commit_initializes_git_without_commit(tmp_path):
    r = run("scaffold.py", "nocommit", "--dest", str(tmp_path), "--no-test", "--no-commit")
    assert r.returncode == 0, r.stderr
    repo = tmp_path / "nocommit"
    assert (repo / ".git").is_dir()
    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True)
    assert status.stdout and all(line.startswith("??") for line in status.stdout.splitlines())
    head = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=repo, capture_output=True)
    assert head.returncode != 0
    assert "no files staged or committed" in r.stdout


def test_scaffold_rejects_no_git_with_no_commit(tmp_path):
    r = run("scaffold.py", "both", "--dest", str(tmp_path), "--no-test", "--no-git", "--no-commit")
    assert r.returncode != 0 and not (tmp_path / "both").exists()


def test_scaffold_refuses_dangling_destination_symlink(tmp_path):
    destination = tmp_path / "projects"
    destination.mkdir()
    unrelated = tmp_path / "must-not-be-created"
    (destination / "new-project").symlink_to(unrelated, target_is_directory=True)
    result = run("scaffold.py", "new-project", "--dest", str(destination), "--no-test", "--no-git")
    assert result.returncode != 0 and "already exists" in result.stderr
    assert (destination / "new-project").is_symlink()
    assert not unrelated.exists()


def test_new_domain_creates_all_layers_and_registers_it(tmp_path):
    repo = _scaffolded(tmp_path)
    r = new_domain(repo, "orders", "--path", "/orders", "--method", "POST")
    assert r.returncode == 0, r.stderr
    k = repo / "src/main/kotlin/cz/example/perf"
    for layer in ("data/OrdersFeeders", "requests/OrdersRequests", "steps/OrdersSteps",
                  "flows/OrdersFlows", "usecases/OrdersUseCases"):
        assert (k / "domain/orders" / f"{layer}.kt").exists()
    assert (k / "simulations/domain/orders/OrdersMixSimulation.kt").exists()
    assert (repo / "src/test/resources/orders/orders.csv").exists()
    assert ".post(Paths.ordersEndpoint)" in (k / "domain/orders/requests/OrdersRequests.kt").read_text()
    for env in ("test", "prod"):
        assert "ordersEndpoint=/orders" in (repo / f"src/main/resources/env/{env}.properties").read_text()
    assert "OrdersMixSimulation" in (repo / "ci/simulation-data.csv").read_text()
    assert {path.name for path in (k / "domain").iterdir()} == {"orders"}
    assert {path.name for path in (k / "simulations/domain").iterdir()} == {"orders"}
    assert len((repo / "ci/simulation-data.csv").read_text().splitlines()) == 2
    assert "items" not in (repo / "src/main/resources/env/test.properties").read_text()
    assert not (repo / ".github/scripts/check_items_http.py").exists()


def test_new_domain_dry_run_and_refusals(tmp_path):
    repo = _scaffolded(tmp_path)
    before = (repo / "ci/simulation-data.csv").read_text()
    assert new_domain(repo, "orders", "--dry-run").returncode == 0
    assert not (repo / "src/main/kotlin/cz/example/perf/domain/orders").exists()
    assert (repo / "ci/simulation-data.csv").read_text() == before
    assert new_domain(repo, "Bad_Name").returncode != 0
    assert new_domain(repo, "items").returncode == 0                         # no implicit sample
    assert new_domain(repo, "items").returncode != 0                         # now it exists
    assert new_domain(repo, "orders", "--path", "orders").returncode != 0
    empty = tmp_path / "empty"
    empty.mkdir()
    r = subprocess.run([sys.executable, str(repo / ".github/scripts/new_domain.py"), str(empty), "orders"],
                       capture_output=True, text=True)
    assert r.returncode != 0                                                 # not a perf repo


# ---- orchestrator + playbooks ------------------------------------------------------------

PLAYBOOKS = SKILL / "playbooks"
EXPECTED = {"knowledge", "load-testing-basics", "access", "env", "repo", "reviewer"}


def test_orchestrator_is_the_only_agent_and_can_spawn():
    assert [f.name for f in ALL_AGENTS] == ["perf-orchestrator.agent.md"]
    front = re.match(r"---\n(.*?)\n---\n", AGENT.read_text(encoding="utf-8"), re.S).group(1)
    assert "'agent'" in re.search(r"^tools: \[(.*?)\]", front, re.M).group(1)


def test_orchestrator_references_existing_data():
    text = AGENT.read_text(encoding="utf-8")
    for rel in re.findall(r"`(\.github/[^`*{}]+?\.(?:md|json))`", text):
        assert (ROOT / rel).exists(), rel
    for name in EXPECTED:
        assert f"`{name}`" in text or f"{name}.md" in text, name


def test_playbooks_exist_and_use_real_scripts():
    assert {p.stem for p in PLAYBOOKS.glob("*.md")} == EXPECTED
    for p in PLAYBOOKS.glob("*.md"):
        for s in set(re.findall(r"([a-z_]+\.py)\b", p.read_text(encoding="utf-8"))):
            assert (SCRIPTS / s).exists(), f"{p.name}: {s}"


def test_rules_file_carries_safety_rules_and_orchestrator_embeds_them():
    rules = (SKILL / "rules.md").read_text(encoding="utf-8")
    assert "Never read or print the content of `.env`" in rules and "Invent nothing" in rules
    assert "Never submit requests or run load" in rules and "Never commit secrets" in rules
    assert "rules.md" in AGENT.read_text(encoding="utf-8")


def test_orchestrator_has_verification_loop():
    text = AGENT.read_text(encoding="utf-8")
    assert "reviewer" in text and "VERDICT" in text and "at most 3 iterations" in text
    assert "Use the fewest sub-agent calls" in text
    assert "Never perform the worker's task yourself" in text
    assert "You coordinate and verify; workers execute." in text
    assert "If the sub-agent tool is unavailable" in text
    assert "does NOT submit access requests" in text and "explicit confirmation" in text


def test_access_guidance_does_not_collect_unneeded_accounts():
    text = AGENT.read_text(encoding="utf-8")
    access = (PLAYBOOKS / "access.md").read_text(encoding="utf-8")
    assert "Ask for a primary account only if needed for personalized request text" in text
    assert "not a numeric employee number" in text
    assert "Do not collect an account identifier just for general guidance" in access
    assert "Never infer it from the operating-system login" in access


def test_unsupported_access_checks_are_not_offered():
    access = (PLAYBOOKS / "access.md").read_text(encoding="utf-8")
    agent = AGENT.read_text(encoding="utf-8")
    assert "Automated AD, REDiM, SSO and ServiceNow checks are not supported" in access
    assert "no automated AD/REDiM/ServiceNow checks" in agent
    assert "Do not install tools or collect exports to recreate removed integrations" in access


def test_onboarding_does_not_require_api_keys_or_exports():
    access = (PLAYBOOKS / "access.md").read_text(encoding="utf-8")
    agent = AGENT.read_text(encoding="utf-8")
    assert "Do not ask about API keys, employee numbers, exports or SSO" in access
    assert "Accept any user-reported permissions as user-confirmed, not independently verified" in access
    assert "guidance-first" in agent
    assert "Never block local learning on internal permissions" in access


def test_onboarding_reveals_only_the_current_step():
    text = AGENT.read_text(encoding="utf-8")
    assert "Ask one question per turn and wait for the answer" in text
    assert "2-4 short sentences or at most 3 short bullets" in text
    assert "not the full onboarding plan" in text
    assert "do not hide a blocker or a safety warning relevant now" in text
    assert 'rather than repeatedly asking "Is that clear?"' in text
    assert "Do not spawn a worker/reviewer pair for each conversational reply" in text
    assert "no compulsory lecture or wiki refresh" in text
    assert "within 240 words" in text
    assert "only relevant permissions" in text
    assert 'Conditional follow-ups such as "If so, where?" are additional questions too' in text
    assert "What is the local folder of the cloned repository?" in text


def test_permission_guidance_is_scoped_and_evidence_labeled():
    access = (PLAYBOOKS / "access.md").read_text(encoding="utf-8")
    reviewer = (PLAYBOOKS / "reviewer.md").read_text(encoding="utf-8")
    assert "Do not append Artifactory, viewer, API Manager or Alfred groups" in access
    assert "Only an explicitly requested complete checklist" in access
    assert "not the user's membership" in access
    assert "must not trigger the full permission catalog" in reviewer
    assert "pending and user-confirmed items must not be requested again" in reviewer


def test_existing_repository_handoff_requires_available_agent():
    agent = AGENT.read_text(encoding="utf-8")
    repo = (PLAYBOOKS / "repo.md").read_text(encoding="utf-8")
    assert "Only when perf-coding is known to exist in the target checkout" in agent
    assert "Do not assume perf-coding is installed" in repo
    assert "without a separate request" in repo
    env = (PLAYBOOKS / "env.md").read_text(encoding="utf-8")
    assert "--repo <confirmed-repository-url>" in env


def test_onboarding_uses_permissions_for_authorization():
    for path in (AGENT, PLAYBOOKS / "access.md"):
        text = path.read_text(encoding="utf-8")
        assert '"permissions"' in text
        assert '"access rights"' in text
        assert 'not bare "access"' in text


def test_independent_project_requires_its_own_infrastructure():
    repo = (PLAYBOOKS / "repo.md").read_text(encoding="utf-8")
    agent = AGENT.read_text(encoding="utf-8")
    assert "its own Git repository, its own Artifactory repository" in repo
    assert "SAS application/service identity" in repo
    assert "Application Services (SAS)" in repo
    assert "2271351856" in repo
    assert "This catalog does not establish the creation procedure or API-key binding" in repo
    assert "API key associated with that application" in repo
    assert "not installing a new Artifactory server" in repo
    assert "Do not provision Artifactory or API Manager resources automatically" in repo
    assert "Never request, read or print the key in chat" in repo
    assert "Personal permissions, local scaffold and project infrastructure are separate milestones" in agent
    assert "Do not claim onboarding complete merely because the local sample exists" in agent
    assert "SAS application-service record, Git repository, Artifactory repository" in repo
    assert "do not mark project readiness complete until these resources are confirmed" in repo
    assert "not separate onboarding milestones" in repo
    assert "Do not routinely ask for them or block progress on confirming them" in repo
    assert "not readiness for actual project work" in repo
    assert "API-key creation is for a specific application selected in API Manager (APIMAN)" in repo
    assert "confirm that mapping from project documentation or the user" in repo
    assert "do not invent quota values for load testing" in repo
    assert "not proof that a key was created or authorized" in repo


def test_permissions_guidance_covers_both_environments_without_intake_gate():
    agent = AGENT.read_text(encoding="utf-8")
    access = (PLAYBOOKS / "access.md").read_text(encoding="utf-8")
    assert "without asking the user to choose an environment" in agent
    assert "or first confirm existing permissions" in agent
    assert "for both TEST and PROD" in access
    assert "Do not ask which environment the user wants" in access
    assert "not a claim that every permission is mandatory for every task" in access
    assert "shared recommendation" in access
    assert "Do not include georgepete_only_groups for an unrelated project" in access


def test_existing_project_context_precedes_permission_derivation():
    repo = (PLAYBOOKS / "repo.md").read_text(encoding="utf-8")
    access = (PLAYBOOKS / "access.md").read_text(encoding="utf-8")
    agent = AGENT.read_text(encoding="utf-8")
    assert "ask for the SAS identifier or repository URL" in agent
    assert "Onboarding a person is not provisioning the project again" in agent
    assert "Either identifier is enough to begin" in repo
    assert "A repository name prefix is a clue, not proof of its SAS" in repo
    assert "not prove that it exists or that the user belongs to it" in access
    assert "Do not derive Artifactory groups by replacing GEORGEPETE" in access
    assert "Do not invent a write-role suffix from the ADM example" in access


def test_artifactory_guidance_distinguishes_login_roles_and_provisioning():
    access = (PLAYBOOKS / "access.md").read_text(encoding="utf-8")
    for detail in ("660233528", "1017253136", "1017253141", "SAML SSO",
                   "ART_USERS", "ART_<SAS>_READ", "ART_<SAS>_DEPLOY",
                   "ART_<SAS>_DELETE", "active Windows domain account in XUC",
                   "do not recommend by default",
                   "Group membership does not create an Artifactory repository"):
        assert detail in access
    assert "Do not recommend it additionally" in access
    assert "READ is relevant to private repositories" in access
    assert 660233528 in {tree["root_id"] for tree in load(SKILL / "sources.json")["trees"]}


def test_artifactory_application_provisioning_is_documented():
    repo = (PLAYBOOKS / "repo.md").read_text(encoding="utf-8")
    for detail in ("725305449", "1017253184", "1017253206", "1017253231",
                   "fc286a2c87454910fd8f65750cbb3521",
                   "f039cc8a87a68190fd8f65750cbb3506",
                   "not on the user's laptop", "populated overnight",
                   "not the APIMAN application API key",
                   "do not report Artifactory creation as undocumented"):
        assert detail in repo
    assert 725305449 in {tree["root_id"] for tree in load(SKILL / "sources.json")["trees"]}


def test_onboarding_branches_on_resource_existence():
    repo = (PLAYBOOKS / "repo.md").read_text(encoding="utf-8")
    for branch in (
        "Joining versus starting unknown",
        "Joining an existing project, identifiers unknown",
        "Existing project, repository unknown",
        "New project or missing repository, SAS unknown",
        "SAS missing",
        "SAS known, repository existence unknown",
        "SAS known, repository missing",
        "Repository exists, needed permissions missing",
        "Repository exists, needed permissions user-confirmed",
    ):
        assert branch in repo
    assert "a new testing project may use an existing application SAS" in repo
    assert "After SAS provisioning, return to the repository-existence decision" in repo
    assert "A pending request is pending, not provisioned" in repo
    assert "do not invent a form or submit a request" in repo
    assert "It is not a check for SAS or repository existence" in repo
    assert "do not ask them to identify an existing project first" in repo


def test_georgepete_resources_are_reference_not_new_project_defaults():
    repo = (PLAYBOOKS / "repo.md").read_text(encoding="utf-8")
    for reference in ("cmdb_ci_service_auto.do", "sys_user_group.do",
                      "George performance testing", "squad George - Native Labs",
                      "https://github.com/csas-dev/georgepete-georgepete-performance-test",
                      "https://artifactory.csin.cz/artifactory/georgepete-generic-private-local/"):
        assert reference in repo
    assert "Treat the SAS record and API Manager registration as separate records" in repo
    assert "not as default destinations, ownership or permissions for a new project" in repo
    assert "do not assume a new group must be created" in repo


def test_corporate_git_repository_uses_documented_request():
    repo = (PLAYBOOKS / "repo.md").read_text(encoding="utf-8")
    for required in ("1438877154", "1012173546", "a74a1c89db6fa0502493d6a2f3961958",
                     "pete-automation", "Final repository URL",
                     "do not type it into the requested name",
                     "Do not create corporate repositories with `gh repo create`",
                     "Do not manually rename or delete provisioned repositories"):
        assert required in repo
    assert "Corporate remote repositories are requested personally through ServiceNow" in AGENT.read_text()
    sources = {p["id"] for p in load(SKILL / "sources.json")["extra_pages"]}
    assert {1438877154, 1012173546} <= sources


def test_onboarding_does_not_duplicate_greetings_or_questions():
    text = AGENT.read_text(encoding="utf-8")
    assert "produce only the final response" in text
    assert "After asking a question, end the turn" in text
    assert "never to preview or duplicate the next question" in text
    rules = (SKILL / "rules.md").read_text(encoding="utf-8")
    assert "Do not greet or address the user directly" in rules


def test_orchestrator_hands_off_coding_to_the_new_repo():
    text = AGENT.read_text(encoding="utf-8")
    assert "copilot --agent perf-coding" in text
    assert "`coder`" not in text
    assert "copilot --agent perf-coding" in (PLAYBOOKS / "repo.md").read_text(encoding="utf-8")


def test_agents_are_written_in_english():
    files = [*ALL_AGENTS, *PLAYBOOKS.glob("*.md"), SKILL / "rules.md", SKILL / "glossary.md",
             *(TEMPLATE / ".github").rglob("*.md")]
    slovak = re.compile(r"[ďľĺŕňťôäěščřžýáíéú]|\b(nikdy|pravidl|používateľ|odpovedaj|krok)\w*", re.I)
    for f in files:
        hits = [m.group(0) for m in slovak.finditer(f.read_text(encoding="utf-8"))]
        # REDiM/Czech UI labels are quoted on purpose (Nová žádost, Nastavit oprávnění, Přístupy)
        hits = [h for h in hits if h.lower() not in {"ž", "á", "í", "ě", "š", "ř", "é", "ú", "ý", "č", "ň"}]
        assert not hits, f"{f.name}: non-English text {hits[:5]}"


def test_reviewer_playbook_is_read_only_verdict():
    text = (PLAYBOOKS / "reviewer.md").read_text(encoding="utf-8")
    assert "VERDICT: PASS" in text and "VERDICT: FAIL" in text


def test_agent_frontmatter_is_valid_yaml():
    import yaml
    front = re.match(r"---\n(.*?)\n---\n", AGENT.read_text(encoding="utf-8"), re.S).group(1)
    data = yaml.safe_load(front)
    assert data["name"] == "perf-orchestrator" and "agent" in data["tools"]


def test_run_readiness_checklist_is_guidance_only():
    coding = TEMPLATE / ".github/skills/perf-coding"
    text = (coding / "run-readiness.md").read_text(encoding="utf-8")
    for needed in ("Additionally for PROD", "Normal Change", "API Manager", "Alfred", "24 hours",
                   "Unknown is not missing", "Never ask for or print API key", "guidance only"):
        assert needed in text, needed
    assert "run-readiness.md" in (coding / "rules.md").read_text(encoding="utf-8")
    assert "run-readiness.md" in (TEMPLATE / ".github/agents/perf-coding.agent.md").read_text(encoding="utf-8")


def test_run_readiness_separates_project_facts_from_reference_examples():
    coding = TEMPLATE / ".github/skills/perf-coding"
    text = (coding / "run-readiness.md").read_text(encoding="utf-8")
    common, reference = text.split("## GEORGEPETE reference only")
    assert "24 hours" not in common and "Normal Change" not in common
    for needed in ("pending", "not_applicable", "metadata only", "client machine", "PRCheck",
                   "runner", "stop", "PRED", "not bundled", "not a mock"):
        assert needed in common, needed
    assert "24 hours" in reference and "Normal Change" in reference
    assert "open design questions" in reference
    assert "03:00" not in common
    assert "## Before a shared-environment run" in (TEMPLATE / "README.md").read_text(encoding="utf-8")

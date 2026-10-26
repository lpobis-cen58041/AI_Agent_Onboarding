# Copilot instructions for perf-agent

This repo is a Copilot custom agent (`perf-orchestrator`) for non-technical onboarding into the GEORGEPETE / PERF
(Gatling load tests) process. It holds agent text, data, Python helper scripts and a sample-repo template. It does not contain the load tests.

## Setup, tests
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt   # dev = pytest, pyyaml
python -m pytest -q tests                                  # full suite (CI: .github/workflows/test.yml)
python -m pytest -q tests/test_repo.py::test_agent_safety_rules_present   # single test
python -m pytest -q tests/test_env_local.py                # local readiness checks
python tests/run_scenarios.py [--only ID ...] [--runs 3] [--model MODEL] [-v] [--slow]  # optional, needs logged-in `copilot`, not in CI
python tests/run_scenarios.py --onboarding --list           # preview 18 multi-turn paths, no credits
python tests/run_scenarios.py --onboarding -j 1 -v          # opt-in model conversations, consumes credits
```
No linter is configured for the Python code. The template is checked separately: CI runs
the default clean scaffold, its first generated domain, and an explicit `--demo` scaffold
with `./mvnw -q test detekt:check` (Java 17).

## Architecture
- **Agents:** `.github/agents/perf-orchestrator.agent.md` is the only agent in this repo. It plans, delegates and verifies
  but does no worker tasks itself. Sub-agents (knowledge, access, env, repo, reviewer) are not written by hand. The orchestrator builds each one
  at runtime from `.github/skills/perf-setup/playbooks/<name>.md` + `rules.md` + facts. New execution, source-based guidance and changes go through a worker, then an independent
  reviewer (`playbooks/reviewer.md`, read-only, returns `VERDICT: PASS/FAIL`), with at most 3 fix iterations.
  To change behaviour, edit the playbooks and rules. Do not add more agents (a test enforces a single orchestrator). Reload VS Code after editing agent text.
- **Onboarding UX:** one short step and one question at a time. Intake and relaying existing reviewed guidance need no new worker/reviewer pair.
  Ask for one missing fact, not an existence question followed by a conditional identifier/path question.
  Single-step replies target 120 words (normal onboarding ceiling 240); a full catalog requires an explicit request.
  For contributing code, start with the confirmed GitHub contributor role, not all project/shared groups.
  Source-backed recommendations do not verify membership. Preserve unknown/missing/pending/user-confirmed states.
  Default to practical guidance and optional `check_env.py --local-only`; no automatic internal access audits, API-key questions,
  SSO, exports or wiki refreshes. Pending rights do not block local setup. Automated AD/REDiM/ServiceNow verification
  is not supported. User-confirmed access is not independently verified.
  First distinguish joining an existing project from starting from scratch, unless already clear.
  For an existing project, ask for its SAS or repository URL before project-specific recommendations;
  for a new project, guide SAS/repository decisions progressively.
  Reuse existing resources; derive permissions from confirmed project mappings and intended tasks, not guessed
  group names or default administrator roles. `access.json` groups are shared API Manager/Alfred recommendations.
  `georgepete_only_groups` applies only to explicit work on the existing GEORGEPETE project/resources.
  Personal permissions do not replace project provisioning: guide the project's own Git repository, Artifactory
  repository and SAS application/service identity (Application Services), with the required API Manager registration
  and an API key associated with that application. SAS is not synonymous with API Manager. Follow the repo
  playbook; do not collect key values or claim infrastructure readiness from successful local scaffolding.
  Corporate remote repositories use the documented ServiceNow request with an existing SAS and automatic name
  prefix, never direct GitHub creation. See the repo playbook for naming, role requests and change restrictions.
- **Data (`.github/skills/perf-setup/`):** `access.json` (Redim groups per env and REDiM portals),
  `tickets.json` (manual software-installation guidance), `sources.json` (Confluence pages/trees to snapshot), `glossary.md`
  (terms for non-technical users), `wiki/` + `manifest.json` (snapshots, `wiki/_INDEX.md`; git-ignored).
- **Scripts (`.github/scripts/`, run with venv active):** `wiki.py sync|status|refresh` (Confluence snapshots),
  `check_env.py --local-only` (Java 17, Git, IDE; omit the flag only for explicit GitHub/Artifactory troubleshooting),
  `scaffold.py <name> --dest <dir> [--runner X] [--no-test] [--no-git | --no-commit]`.
  New projects are infrastructure-only by default. `--demo` explicitly includes the items example,
  its data/simulation/CI row and optional mock suite. Never add that flag without a demo request.
  `install_coding_agent.py <checkout>` previews an agent-only installation; applying requires
  explicit approval of its `plan_sha256` with `--apply <hash>`. Conflicts/unsupported layouts block.
  `sync_wiki_pages.py` holds shared Confluence auth and the `.env` loader; `crawl_confluence.py` supplies tree traversal.
- **Template → handoff:** `scaffold.py` copies `.github/skills/perf-setup/template/` (Gatling + Kotlin, Maven wrapper,
  detekt, domain layout) into a new local repo. That repo has its own `perf-coding` agent, coder/reviewer playbooks, and
  `.github/scripts/new_domain.py`. Coding happens there (`cd <repo> && copilot --agent perf-coding --model gpt-6-astra -i "Start"`), never in this repo.
  The source template contains opt-in sample assets for guidance/testing; default scaffolding excludes
  them and starts with empty env keys/CI mappings. Shared MixBuilderTest works without domains.
  A new orders request must not implicitly recreate items. Existing repos are never auto-cleaned.
  Existing project checkouts may not contain that agent: use their own documented workflow, and do not scaffold
  over them or install template tooling without a separate request.
  A requested existing-checkout installation uses the repo playbook's preview/approval/apply path,
  never a template copy or automatic overwrite. The installer does not migrate build/code/CI/config.
  The coding agent routes new domains, existing requests, journeys/mixes and unit tests separately.
  A fresh Start/greeting begins the domain/test interview without a repository audit; `-i` sends that
  first message automatically. Troubleshooting is secondary to the selected domain/test task.
  Open-ended coding requests use progressive intake: new/existing, domain, call contract, data and mix;
  confirm the assembled change before implementing, but skip intake for complete explicit requests.
  Only new domains use `new_domain.py`; existing-domain changes preserve unrelated behavior and reuse simulations.
  Both orchestrators use GPT-6 Astra (`gpt-6-astra` in CLI launch commands).
  Orchestrators inspect via read/search, not shell commands such as cat/git/curl.
  The coding orchestrator has one approved exception: `python .github/scripts/task_state.py ...`
  for local bookkeeping only. The helper records sourced facts, revision-bound approval and
  baseline/coder/reviewer evidence; it never executes checks or edits source. Code-only acceptance
  needs current approval, independent criterion assessment and matching code fingerprints.
  Builds/tests/source edits remain worker responsibilities; role isolation is not technically enforced.
  A bare "sure" is not a mock URL: require a confirmed owned loopback target and approved run limits.
  If no mock exists, offer creation only with permission. Run-only tasks still require independent evidence review.
  Unit tests/static checks do not prove HTTP behavior or achieved RPS. `usersPerSecond` (legacy `targetRps`) means user arrivals.
  Template changes apply to newly generated repos; do not silently update previously generated projects.
- **Tests:** `tests/test_repo.py` runs deterministic checks with no model, no network, and no submissions. It covers JSON configs, agent frontmatter/safety
  rules/script references, no tracked secrets or snapshots, `py_compile` of every script, local-only readiness,
  template invariants, `scaffold.py` and `new_domain.py`. If you change agent text, playbooks,
  rules or scripts, keep these tests in sync. `tests/scenarios.json` + `run_scenarios.py` check model answers with `must`/`must_not` regexes.
  `tests/onboarding_scenarios.py` generates the onboarding decision matrix. Its turns resume the same CLI session;
  `test_scenario_runner.py` verifies coverage and runner behavior offline. Keep model runs opt-in, not in pytest/CI.
  Native `interactive_cli` regressions require POSIX and `-j 1`. Native single-turn checks expose `ask_user`;
  multi-turn checks resume one session using text questions and isolate each turn's appended events.
  They do not test clicking native dialogs or replace an uncoached beginner trial.
  Coding guidance scenarios run read-only in the template. The two opt-in coding end-to-end scenarios use
  disposable scaffold fixtures, check resulting files and preserved configuration, and independently run Maven
  test/detekt before cleanup. Selected synthetic fixture files and check results are included in the conversation log.
  Fixtures use `--no-git`; the existing-install rehearsal initializes Git without a commit for compatibility.
  Process checks require full rules in every task and reject direct orchestrator execution except
  explicitly enabled task-state commands in coding scenarios; worker tool calls
  are distinguished by parentToolCallId. Read-only guidance tests do not prove behavior with all tools enabled.

## Conventions
- `rules.md` is pasted **verbatim** into every sub-agent task. The onboarding agent retains its immutable
  rules section. Coding shared rules have one canonical owner, `rules.md`; repository conventions,
  intake, endpoint contracts, state protocol and role procedures live in their respective documents.
- Never read or print `.env` and never ask for tokens in chat. `.env.example` lists the variables with no values. Never commit
  `.env`, tokens, cookies, `wiki/` or `manifest.json` (snapshots are internal content).
- Access requests are prepared, not submitted. The user submits them in REDiM (tile *Windows*), not in ServiceNow.
  Automated permission checks and request submission integrations are not supported.
- Never run load against TEST/PROD for the user. Do not suggest PROD tests without approval.
- Invent nothing. Facts come from wiki snapshots/data files. Business matters (status, deadlines, people) are out of
  scope, so point to the team.
- Agent, playbook and rule texts are in English (tested), and responses are in English. Parts of README.md are in Slovak.
- Template stays generic (no real endpoints/data/internal hosts). Its `env/test.properties` and `env/prod.properties` keep identical
  keys, CI rows must point to existing simulations, and use-case weights must sum to 100. Change the template only here,
  and put user code only in scaffolded repos.
- Wiki changed: run `wiki.py status`, then `refresh`, then check whether `access.json`/`tickets.json`/agent text need updates. To add a
  page, add it to `sources.json` and run `wiki.py sync`.

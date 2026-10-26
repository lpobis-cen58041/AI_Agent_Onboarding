# perf-agent

Copilot agent **`perf-orchestrator`** guides beginners through setting up a local
Gatling/Kotlin load-test project. It uses Confluence snapshots for internal
instructions, explains access requests when needed, checks local prerequisites
and creates a new repository with its own **`perf-coding`** agent.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Open this folder in VS Code and select `perf-orchestrator`, or use Copilot CLI:

```bash
copilot --agent perf-orchestrator --model gpt-6-astra
```

The harness must support sub-agents (Run Subagent in VS Code). Without delegation,
the orchestrator reports a blocker rather than executing worker tasks itself.
Reload VS Code after changing agent instructions.

## Onboarding

The agent asks one question at a time and shows only the current next step:
establish the project, explain the permissions needed now, and guide local
preparation or the missing resources. A new local repository is optional, not a
replacement for an existing project. Pending rights do not block unrelated local work.
User-confirmed access is not presented as independently verified.
Single-step answers target 120 words, with a normal onboarding ceiling of 240.
For a code contributor the first recommendation is the confirmed GitHub role
and its request portal, not the entire permission catalog. Shared API Manager/
Alfred guidance and Artifactory roles come at their service step or on request.
An explicitly requested full checklist can be longer. Unknown, missing, pending
and user-confirmed states are retained without repeated questions or requests.

Permissions are requested personally in REDiM using its **Windows** tile;
general onboarding presents recommended project permissions for both TEST and PROD
without an environment-selection question or an existing-permissions interview.
First establish whether the user is joining an existing project or starting
from scratch. For an existing project, ask for its SAS or repository URL if
missing; for a new project, guide the resource decisions progressively.
Existing projects reuse their resources; joining a team does not
mean creating another repository. Recommend project-specific permissions from
confirmed mappings and the intended task, not guessed group names or default
administrator roles. Shared recommendations are `XUC\APIMAN_DEVELOPER`,
`CSINT\Alfred_Authentication_Users` and `CSINT\Alfred_Performance_Testing`.
The repo playbook contains the branching flow: reuse an existing repository,
or establish/reuse SAS before requesting a missing repository, then guide the
user's permissions. A new testing project may already have an application SAS;
an existing project may still lack a test repository. Skip questions already
answered and do not repeat pending requests.
GEORGEPETE repository write, Artifactory and viewer groups are reference-only
in `access.json` (`georgepete_only_groups`), not requirements for a new project.
Separately, a real project needs its own remote Git repository, Artifactory
repository and SAS application/service identity, with the required API Manager
registration and an API key associated with that application.
In APIMAN, key creation selects a specific application; it is not a generic
personal key. Reuse the project's existing APIMAN application when available
and confirm its mapping to SAS rather than guessing from similar names.
The [application-layer catalog](https://cnfl.csin.cz/spaces/APMINTEGRACE/pages/2271351856)
calls these **Application Services (SAS)**; it is not itself an API Manager
registration guide. Exact provisioning and key-binding procedures still need
documented confirmation. The agent guides the approved provisioning
procedures one step at a time; it does not provision Artifactory/API Manager
automatically or handle key values. A local scaffold is not evidence that
these resources are ready, but coding can continue while provisioning is pending.
The repo playbook includes the user-supplied GEORGEPETE example: its SAS is a
ServiceNow CMDB record, alongside an assignment group, owner, Git repository and
Artifactory repository. These are reference resources, not defaults for new
projects. Onboarding focuses on external resources to arrange: SAS record,
Git repository, Artifactory repository and API Manager/API-key integration.
Owner and assignment group are team context, not separate onboarding milestones;
the agent asks for them only if needed by a provisioning procedure.
Local preparation may continue while they are pending, but is not reported as
readiness for actual project work.
Software-installation guidance is in `tickets.json`. Automated AD, REDiM,
ServiceNow, SSO and export checks are not supported. No API key or employee
identifier is needed for general onboarding.

Artifactory guidance separates SAML sign-in, project permissions and repository
provisioning. `ART_USERS` enables sign-in without project rights and is unnecessary
with an existing project `ART_*` group. Documented project roles are
`ART_<SAS>_READ` (private reads), `ART_<SAS>_DEPLOY` (read/deploy) and
`ART_<SAS>_DELETE` (also delete/overwrite). Public reads are already available to
SAML-authenticated users. The agent confirms actual group mappings and recommends
only the necessary role; membership does not create an artifact repository.
For missing project artifact storage, the repo playbook links the documented
ServiceNow local Artifactory repository form (SAS, package type, visibility).
Third-party proxy repositories use a separate approval route; reuse existing
proxies first. Provisioning and personal REDiM membership are distinct steps.
The platform documents overnight GitHub Artifactory secret population for
existing repositories under the SAS, not immediate readiness. Those credentials
are separate from the APIMAN application API key.

Corporate GitHub repositories are requested through ServiceNow **Add repository
to GitHub**, not created directly with the CLI. The request selects an existing
SAS, which automatically supplies the name prefix. The testing guide specifies
`pete-automation` for devops PeTe repositories; confirm applicability to the
project. The repo playbook links the forms and naming rules. Do not manually
rename/delete provisioned repositories; changes must follow the request workflow.

### New project by default; demo only on request

```bash
# Infrastructure and agent only; no sample domain:
python .github/scripts/scaffold.py my-perf-project --dest ~/dev
# Explicit learning/demo project including items:
python .github/scripts/scaffold.py my-perf-demo --demo --dest ~/dev
```

Onboarding uses the first mode unless you explicitly request a demo. No extra mode-selection
question is needed. Both modes keep the existing build/Git options (`--no-test`, `--no-git`,
`--no-commit`); by default scaffolding runs unit tests and initializes Git with a first commit.
When commits are not allowed, `--no-commit` still creates the local Git repository (`git init`)
without staging or committing, so onboarding need not drop Git entirely.
The clean project includes configuration/auth/mix helpers, infrastructure unit tests and the coding
agent, but no domain, simulation, sample CSV, mock checker or sample CI mapping. Matching empty
env key sets and a header-only `ci/simulation-data.csv` are valid until the first domain is added.
The first `orders` generation adds only orders. Existing repositories are not migrated or cleaned.
The source template retains demo assets for `--demo` and read-only example scenarios; the scaffold
excludes them while copying the default project, before any build or Git initialization.
Template build output (`target/`), local Git metadata, IDE caches and task records are never copied.
Maven will create a fresh gitignored `target/` when checks run; this is generated output, not a
deviation from the source layout or an extra domain.

After creating the project, continue coding inside the new repository:

```bash
cd <repo>
copilot --agent perf-coding --model gpt-6-astra -i "Start"
```

`-i "Start"` sends the opening message automatically so the agent asks about a new or
existing domain immediately. Without `-i`, type `Start` after the CLI opens. `/init`
generates repository instructions; it is not the domain/test workflow.

For an existing project, use its own setup instructions. The agent-specific
command above is offered only when `perf-coding` is known to be available in
that checkout; onboarding does not install it or replace files automatically.

### Install the coding agent in an existing repository

Reuse the existing local checkout; clone the confirmed project remote only if it is not already
on your machine. Cloning and GitHub permissions are separate from this local installer.
From **this onboarding repository**, preview the installation:

```bash
python .github/scripts/install_coding_agent.py /absolute/path/to/existing-checkout
```

The default is read-only: it reports structural compatibility, every file to add/keep/conflict,
limitations and a `plan_sha256`. Review the preview, then explicitly approve that exact plan:

```bash
python .github/scripts/install_coding_agent.py /absolute/path/to/existing-checkout \
  --apply <plan_sha256-from-reviewed-preview>
```

The hash binds the checkout, inspected compatibility inputs and agent payloads. If they change,
review a new preview rather than reusing the old approval. Blocked plans cannot be applied.
The installer only adds the coding agent, its guide/rule/playbook files, repository conventions,
`task_state.py`, `new_domain.py` and `.perf-coding/.gitignore` (to keep task records local).
Identical files are kept; differing files, including existing `.github/copilot-instructions.md`,
are conflicts requiring manual reconciliation. There is no overwrite, merge or force flag.
Review/adapt existing instructions as a separate change; rerun the preview after reconciliation.
It does not stage, commit, clone, run a build/HTTP, or change application code, tests, `pom.xml`,
the root `.gitignore`, CI, load settings or dependencies. It does not install the template's HTTP fixtures.

This first version supports the template-compatible `cz.example.perf` Maven/Kotlin layout and helper
APIs (including the existing mix test/bootstrap and matching env keys). Other packages, Gradle projects,
different helper APIs or missing prerequisites are blocked for a separately scoped adaptation, not
automatically converted. A structural pass is not proof of compilation, agent/model availability or
API correctness. Symlinked inspected/installation paths are rejected. Existing uncommitted work is preserved.

After installation, review the diff and run `./mvnw -q test detekt:check` in the target checkout.
Resolve baseline/build blockers before coding; these commands may download dependencies but do not
run scenario HTTP. The onboarding agent requests independent review before handing off:
`copilot --agent perf-coding --model gpt-6-astra -i "Start"`.
Keep tool approvals enabled. Existing installations are not automatically upgraded.

## Confluence snapshots

General guidance and local setup do not require Confluence credentials.
To download internal instructions, copy `.env.example` to `.env` and set
`CONFLUENCE_TOKEN` locally (Confluence Personal Access Token). `CONFLUENCE_COOKIE`
is an alternative. Never paste either value into chat.

```bash
python .github/scripts/wiki.py sync --no-browser
python .github/scripts/wiki.py status --no-browser
python .github/scripts/wiki.py refresh --no-browser
```

`sync` downloads missing snapshots; `status` compares them with Confluence;
`refresh` replaces them using `sources.json`. A refresh removes snapshots not in
that configuration. Snapshots and the manifest are git-ignored.
Without `--no-browser`, the shared helper can fall back to an existing Edge
session via `browser-cookie3`; corporate SSO compatibility is environment-dependent.

## Maintained tools

| Tool | Purpose |
|---|---|
| `.github/scripts/wiki.py` | Single entry point for snapshot sync, comparison and refresh |
| `.github/scripts/check_env.py --local-only` | Java 17+, Git and IDE readiness; no network checks |
| `.github/scripts/check_env.py` | Explicit GitHub/Artifactory connectivity troubleshooting; not a full permission audit |
| `.github/scripts/scaffold.py <name> --dest <dir> [--demo]` | Create an infrastructure-only project (or explicit items demo), run Maven unit tests, initialize Git and commit |
| `.github/scripts/install_coding_agent.py <checkout>` | Preview a compatible existing checkout; `--apply <plan_sha256>` installs only agent files without overwrites |
| `.github/scripts/new_domain.py` in the created repo | Generate a domain skeleton and register its simulation |

`sync_wiki_pages.py` and `crawl_confluence.py` supply shared Confluence
authentication, Markdown conversion and page-tree traversal to `wiki.py`.
`truststore` uses the OS certificate store; `browser-cookie3` supports the
Confluence Edge-cookie fallback. Neither requires Playwright or a downloaded browser.

## Architecture and maintenance

- `.github/agents/perf-orchestrator.agent.md`: onboarding coordinator.
- `.github/skills/perf-setup/playbooks/` and `rules.md`: worker tasks, safety rules
  and independent review. Related work is bundled; intake and relaying reviewed
  guidance do not spawn another worker/reviewer pair.
- `access.json`, `tickets.json`, `sources.json`, `glossary.md`: group names,
  manual software-request guidance, wiki sources and beginner terminology.
- `.github/skills/perf-setup/template/`: generic Gatling/Kotlin project,
  domain generator, coding agent, tests and CI. Keep endpoints and data synthetic.

Orchestrators coordinate and verify; workers execute. A completed outcome gets
an independent reviewer and at most three correction iterations. VS Code tool
inheritance is not permission isolation: keep terminal approvals enabled.

Add wiki pages to `sources.json`, then sync or refresh. After a wiki update,
check relevant group names and instructions. Change the sample project only in
the template; actual test development happens in scaffolded repositories.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q tests
```

Deterministic tests cover configuration, agent contracts, script references,
local-only checking, repository hygiene, scaffolding and domain generation.
CI builds a clean scaffold, adds its first orders domain, and builds an explicit demo scaffold
with Maven unit tests and `detekt:check`.

Optional model-driven scenarios require a logged-in Copilot CLI and consume credits:

```bash
python tests/run_scenarios.py --only new-user-no-rights --runs 1
# Focused permission-scope and existing-repository regressions:
python tests/run_scenarios.py --only shared-permissions-overview unknown-project-contributor-role existing-repository-without-coding-agent local-checkout-single-question onboarding-hands-off-coding -j 1 -v
```

Use `--slow` to include the coding end-to-end scenarios. These scenarios are not
part of CI.

### Coding-agent validation

The coding agent handles new domains, endpoints in existing domains, journeys/use cases,
mix changes and unit tests separately. It uses the generator only for a new domain and
preserves existing requests, simulations and CI mappings when extending one. Missing API
contracts and traffic weights are questions for the user, not silent defaults.
The documented launch sends **"Start"** automatically; a fresh greeting also starts the intake.
Its primary job is adding/changing domains and tests, not a repository or documentation audit.
It asks new/existing domain, then the domain, API call and needed contract/data/mix details,
one question at a time. Known facts are skipped. It confirms the assembled change before
delegating implementation; a complete explicit implementation request can proceed directly.
This follows the new-domain versus existing-scenario distinction in the curated wiki guidance
(source page 2318992259); the generated repository carries generic instructions, not internal snapshots.
These instructions are copied into newly scaffolded repositories; existing copies are not
automatically upgraded.
New scaffolds also include an optional `python3 .github/scripts/start_coding.py` launcher.
It starts the guided coding agent with session-scoped command-prefix approvals only for
`python`/`python3` calls to `task_state.py` and `new_domain.py`; `--resume [SESSION_ID]` resumes
without restarting intake. This trusts those scripts and their arguments, not arbitrary Python,
and does not change global configuration or override existing CLI permission modes.
The direct CLI launch keeps normal prompts. Existing repositories and the agent-only installer
are unchanged; the launcher is not silently installed into them.

Endpoint intake is technical and conditional: relative path, missing method, expected HTTP status,
then relevant parameters/profile/payload/assertions. It does not require a business interview.
`endpoint-contracts.md` separates routing/auth profiles from methods and body formats.
The source guidance is [02 - Testovací scénáře](https://cnfl.csin.cz/pages/viewpage.action?pageId=2134087449)
(version 14) and [Architektura WebAPI](https://cnfl.csin.cz/pages/viewpage.action?pageId=655922429)
(version 23), read on 2026-10-16 through the local Confluence script.
The first distinguishes WebAPI web/mobile routes, direct public resources and AuthMonitoring;
its production scope excludes active operations. The second describes gateway routing/security and
WebAPI/MiLa/IWA instances, not a complete endpoint schema or a method/status catalog.
Do not invent missing methods, expected statuses or transaction/risk mappings from these pages.
Only generic contract questions are shipped in the template; internal hosts/routes/identities stay
out of generated projects. Form/multipart and HEAD/204 handling are general HTTP guidance, not claims
that these two pages specify every such contract. Existing local-mock-only execution rules remain.
Most read-only guidance scenarios use autonomous `copilot -p` with a read-only tool allowlist,
omitting `ask_user` but not requesting `--no-ask-user`. They check text responses, not the native
interactive interview. Scenarios marked `interactive_cli` instead use actual `copilot -i` and
capture structured session events through a POSIX pseudo-terminal. Single-turn native checks allow
`ask_user`; multi-turn checks omit it to exercise the documented text-question fallback, not dialog
selection/clicking. Each scripted reply resumes the same session UUID in a new interactive process.
Only events appended during that turn count as evidence; old questions cannot make a new turn pass.
These native scenarios require `-j 1`; parallel PTY runs are not supported by this harness.
Only the known fixture's folder-trust dialog is approved automatically, never command/edit permissions.
Fully specified scaffold execution scenarios use `--no-ask-user`.

The coding agent now maintains local, gitignored task records with
`.github/scripts/task_state.py`. They retain sourced facts, current contract revision and approval,
baseline/coder/reviewer evidence and the final acceptance decision. Corrections invalidate approval;
code fingerprints prevent accepting stale reports. Independent criterion assessment is required in
addition to successful checks. The orchestrator has a narrow bookkeeping-command exception, not
permission to implement code or run checks itself.
Reviewers use the read-only `validate-report` action before handing back their exact report JSON.
It checks the same schema and evidence gates as persistence, without changing the task or approving
the result. Formatting corrections stay with the same reviewer and reuse actual check evidence.

Instruction ownership is explicit: shared safety/evidence rules in `rules.md`, repository conventions
in `copilot-instructions.md`, orchestration in the agent, intake/implementation paths in the guide,
endpoint details in `endpoint-contracts.md`, record protocol in `task-state.md`, and role-specific work
in the two playbooks. This does not add agents, technical role isolation or automatic project updates.
The record organizes reported evidence; it cannot authenticate worker identities or prove execution.
Code-only tasks use this lifecycle; separately approved HTTP/run-only work keeps its existing rules.

```bash
# Read-only guidance checks; each consumes model credits:
python tests/run_scenarios.py --only coding-existing-endpoint-guidance coding-test-kind-clarification coding-mix-needs-weights coding-post-contract-clarification coding-validation-boundaries -j 1 -v
# Interactive intake, including corrections and declining implementation:
python tests/run_scenarios.py --only coding-interactive-new-domain coding-interactive-existing-domain -j 1 -v
# Bare startup/greeting, without telling the agent which question to ask:
python tests/run_scenarios.py --only coding-startup coding-greeting -j 1 -v
# Actual implementation in disposable test fixtures, not your project:
python tests/run_scenarios.py --only coding-agent-adds-domain-end-to-end coding-agent-extends-domain-end-to-end -j 1 -v
# Native missing-domain question, unchanged natural prompt, three fresh sessions:
python tests/run_scenarios.py --only coding-unknown-existing-domain --runs 3 --timeout 120 -j 1 -v
# Resumed native text interviews, including status correction and declining implementation:
python tests/run_scenarios.py --only coding-interactive-new-domain coding-interactive-existing-domain coding-endpoint-json-patch-intake --runs 3 --timeout 120 -j 1 -v
# Explicit approval for generated-flow HTTP on owned loopback mocks in disposable fixtures:
python tests/run_scenarios.py --rehearsal --timeout 600 -j 1 -v
```

The end-to-end cases create a new `orders` domain in a clean project or explicitly use `--demo`
to extend existing `items` with a detail request and a 70/30 mix. The new-project case also checks
that items assets remain absent. They check required file content, unchanged infrastructure and an
independent `./mvnw -q test detekt:check` before deleting the fixture. Selected synthetic
source files and the build result remain in the conversation log for inspection.
`--rehearsal` selects these two implementation cases only. The existing-domain fixture first
removes its bundled agent, installs it with the real preview/hash-bound installer and verifies
that all other fixture files remain unchanged. After independent build, artifact and task-acceptance
checks pass, a separate harness runs the actual generated flows: one `orders` request for the fresh
path; one existing `items` browse and one generated detail request for the installed-agent path.
Each owned mock uses an ephemeral `127.0.0.1` port, at most two users and ten seconds of simulation
time, disables redirects/warm-up, and checks exact paths/counts plus zero failed requests.
The harness removes its temporary simulation and stops the server in cleanup; HTTP evidence
is retained in `.http.json`. Maven has a separate 240-second timeout and process-tree cleanup.
This is a coding-entry rehearsal in compatible synthetic repositories, not a complete beginner
onboarding trial or proof of arbitrary endpoint support. Normal model scenarios do not run HTTP;
`--rehearsal` is the explicit opt-in and is incompatible with `--onboarding`.
The 2026-10-20 validation passed 289 deterministic tests and both code-only end-to-end paths:
clean-project `orders` generation and an existing-domain extension. Each used exactly one coder
and one independent reviewer, validated the review report before handoff, passed an independent
Maven unit/static check and persisted final acceptance. The clean path also checked that no `items`
assets appeared and that `docs/orders.md` was generated.
The TEST-via-CI, laptop-to-TEST and GEORGEPETE-PROD readiness checklists each passed two fresh
guidance-only runs, including status preservation, project-specific scope and the 180-word ceiling.

Earlier clean-project trials exposed incomplete generator evidence, reconstructed pre-edit state and
an incompatible reviewer JSON handoff. Approval-bound fingerprints, retained baseline manifests,
ordered task-bound generator checks and read-only report validation address these failures.
The failed logs remain for diagnosis. The successful runs are individual samples, not a reliability
guarantee; this validation did not run a generated-flow HTTP rehearsal or shared TEST/PROD load.

Before the clean-project default change, both coding entry paths passed locally with CLI 1.0.100-1:
the scaffold already included items, and its new `orders` flow produced
exactly one successful request; the installed-agent `items` browse/detail flows produced exactly
two successful requests. Each had independent review, persisted acceptance and an independent
Maven unit/static check before HTTP. These are separate successful runs, not a repeated reliability
sample. Earlier fixture failures remain in the local logs: a macOS temporary-directory alias
prevented installation, and a literal `toSet` assertion incorrectly rejected equivalent `distinct`
uniqueness checks. Both harness issues have regression coverage.
Failed process checks also retain the delegation prompts for diagnosis; keep those logs private.
Source-context checks accept an observed file read or the complete literal source body in a task
(the document title may differ); a filename or partial quote is not sufficient.
Every coder/reviewer task must carry the full rules, not just a safety phrase. Tool ownership
is recorded so a worker's shell command is allowed but direct orchestrator execution is rejected.
Astra coordinates and accepts results, selecting worker models by task complexity: GPT-5.4 mini for
routine coding/mechanical review, Astra for complex or uncertain work, subject to supported models
and explicit user choices. Routine code changes use one coder plus one independent reviewer.
The coder carries baseline and pre-existing-edit evidence forward; reviewers do not search session
history to reconstruct it. Final unit/static checks use one `./mvnw -q test detekt:check` invocation
per role, not competing Maven processes. Existing test helpers and focused dependency inspection
reduce rediscovery without weakening assertions or disabling permission prompts.
Every run, including single-turn checks, records its CLI session UUID and worker-model events for
local timing/usage analysis, without extra model calls.
Tool elapsed time can include manual approval waits; compare those separately from execution and
AI credits. Automated fixtures do not reproduce human approval latency.
Intake checks require a question or explicit imperative requesting input (such as "Choose the
expected status"), rather than a question mark alone; summaries without a next input still fail.

### Domain and endpoint use-case coverage

`tests/coding_use_cases.json` is the reviewed coverage inventory: domain create/extend and test-only
changes, endpoint profiles, HTTP methods and payload formats, response rules, dependent calls,
workflow corrections and explicit pairwise combinations. It avoids an unrestricted Cartesian
product; invalid or contract-unsupported combinations are not manufactured. Each entry points to
a model scenario or a deterministic mock case. `pytest` validates catalog completeness and scenario
links without making model calls:

```bash
python -m pytest -q tests/test_coding_use_cases.py tests/test_scenario_runner.py
```

The additional endpoint intake prompts are opt-in because each real model conversation consumes
credits; list/run them explicitly with `tests/run_scenarios.py --list` or `--only ...`. They are
guidance/interview checks, not proof that generated HTTP requests work. For behavioral coverage,
run `python3 .github/scripts/check_items_http.py` from an explicitly scaffolded `--demo` repository.
The checker is omitted from normal new projects, starts/stops its own ephemeral `127.0.0.1` mock, and
expects 27 requests from 13 synthetic users within 15 seconds of simulation time.
It checks the actual sample browse flow plus test-only fixtures for JSON correlation/failure gates,
form/multipart encoding, bodyless responses, per-request header isolation and bounded polling.
It validates actual method/path/query/headers/body and forbidden follow-ups, not only HTTP statuses.
`--check-detectors` additionally verifies that deliberate gate, ID-check, header and poll-bound regressions
fail at runtime in disposable copies. Results are saved under `target/items-http-contract/`.
The separately modified `coding-agent-demo` has additional detail/summary flows and its own
16-request checker; those demo-only extensions are not the source template.
Neither suite validates arbitrary generated endpoint implementations or a corporate/live API contract.
The current release is a supervised pilot, not an autonomous endpoint generator. With CLI
1.0.100-1, the unchanged `coding-unknown-existing-domain` prompt passed three fresh native interactive
sessions: the agent requested the repository/domain decision without edits or delegation.
Autonomous `-p` probes still sometimes explained the blocker without directly asking; adding
`--mode interactive` while retaining `-p` did not reproduce the native interview. Those failed
probes remain evidence of that harness/mode limitation, not successes. Native completion uses
the final content-bearing message and matching `assistant.turn_end`, since interactive sessions
need not emit `assistant.idle`. This single-turn regression does not establish universal reliability.
Native multi-turn text interviews now cover the earlier autonomous PATCH gap: the original six-turn
PATCH conversation completed, including its approval question and refusal to implement. The
new-domain seven-turn interview passed three fresh sessions after fixing a real missing approval
question following a status correction; the existing-domain five-turn interview also passed three
fresh sessions. PATCH passed several completed serial sessions, including a final run after the
cleanup changes. These samples came from separate invocations, not a single uniformly green batch.
Earlier failed runs remain in the logs: autonomous clarification omissions, native cleanup failures,
the correction-turn omission, and a regex that wrongly rejected "expect 204, not 200".
The correction gate now permits rejection of the old status but still rejects expecting 200.
A request to keep execution blocked during intake is distinct from an explicit plan-only refusal:
corrections require a fresh confirmation question; an explicit refusal ends intake without one.
These are scripted replies and resumed processes, not an uncoached beginner or continuous dialog-UI
trial. That human walkthrough and a sharing/history review remain necessary before freezing a
presentation version.
Implementation model scenarios allow execution/editing tools and can take several minutes;
`--only` explicitly opts into them, while `--slow` includes them in the default suite.

Unit tests and static analysis do not execute Gatling scenario HTTP requests. No model test above
runs load against TEST/PROD. Actual HTTP behavior requires the explicit `--rehearsal` opt-in
or a separately requested bounded local-mock run. The template's `usersPerSecond` controls virtual-user arrivals
(`constantUsersPerSec`), not exact HTTP requests per second. Deprecated `targetRps` input and Kotlin
property aliases remain supported; `usersPerSecond` input takes precedence. Invalid rates fail explicitly.
The agent never assumes an example mock URL from "sure": it asks for an owned loopback target
and approved run limits. If there is no mock, it offers creation with explicit permission.
Test execution also gets independent evidence review; a refused connection does not justify retries.
Use `--only coding-mock-ambiguous-consent coding-mock-limits-not-approved` for these guidance regressions.
`--only coding-run-blocker-review` exercises an unavailable target using a reserved, non-listening
loopback port in a disposable fixture and requires independent review of the blocker. The result
may be refusal or timeout depending on the execution environment; it must be reported accurately.

### Multi-turn onboarding matrix

```bash
# Preview the matrix without model calls or credits:
python tests/run_scenarios.py --onboarding --list
# One path first (a real conversation, resumed across turns):
python tests/run_scenarios.py --onboarding --only onboarding-joining-repo-exists-missing -j 1 -v
# All paths; each run consumes model credits:
python tests/run_scenarios.py --onboarding -j 1 -v
```

The matrix covers 18 valid combinations: joining/starting, repository exists /
SAS only / neither exists, and permissions granted/missing/pending. A corporate
repository without a SAS is excluded because provisioning requires SAS.
Each path begins with intake and continues through multiple user replies in
one CLI session; repeated runs use new isolated conversation IDs. Scenarios
check expected guidance at each turn, forbidden environment questions, secret
requests, duplicate provisioning and pending-state handling, plus response size
and question count. Contributor-permission replies must name the confirmed group,
stay within 160 words and omit unrelated service/admin groups; the general limit
remains 240 words. The focused scenarios separately preserve explicitly requested
shared overviews and check unknown mappings, single-question checkout intake and
coding handoff with/without the template agent.
Failures stop that path and `-v` prints its transcript.
Progress is flushed immediately: `START` identifies a run, `WAIT` identifies
the current model turn, `PASS`/`FAIL` completes a turn with elapsed time and
`DONE` completes a run. A model turn can take several minutes (default CLI timeout:
900 seconds). Use `--timeout 120` for a bounded guidance check. The runner reports elapsed time
every 30 seconds, writes stdout JSONL and stderr incrementally, and stops its launched process
tree on timeout/interruption rather than waiting on inherited output pipes. A timeout fails the
scenario; it is not automatically retried or counted as success.
Completed native text turns first request the CLI's documented `/exit`; if it does not close within
five seconds, the runner falls back to process-group cleanup. Pending question dialogs and failures
use process-group cleanup. Darwin's `killpg` can report `EPERM` for zombie-only groups; a reproduced
regression covers this. Permission errors are tolerated only after a successful process-state query
confirms there are no live group members. Live-group permission failures remain errors, with group
states and a traceback in the retained log, not success-shaped fallbacks.
Every new invocation also saves successful and failed conversations as Markdown
under `tests/results/<timestamp>-<unique-id>/`, one file per scenario/run.
User prompts are saved before each model call and answers immediately afterward,
so completed turns survive interruption. Per-turn `.stdout.jsonl` and `.stderr.log` files
preserve partial events, including the active model/tool stage, even if there is no final answer.
Logs record CLI version, requested model and reported model events; an unreported actual model
stays explicitly unknown, never inferred from the request. The startup output prints the directory;
`--log-dir <path>` changes its parent. Logging adds no model calls or credits.
Logs contain prompts/answers and may include internal information or the synthetic
secret-rejection test string; keep them local. `tests/results/` is git-ignored.
The raw event stream can include tool results, local paths, managed settings and internal content.
Nothing is redacted automatically; do not supply secrets, keep the logs local and review before sharing.

This covers the finite decision branches, not every possible wording or
live-system behavior. Synthetic guided replies do not validate actual permissions,
resource provisioning or the VS Code interface. No model scenario is run by
pytest/CI; deterministic tests validate the matrix and runner without credits.
Question counting excludes URL query delimiters, but still rejects multiple
questions in prose. Missing-resource paths use a synthetic project with an
explicitly supplied contributor-group mapping, so they do not contradict the
known GEORGEPETE resources or reward invented permission names. Known-repository
paths retain the documented GEORGEPETE example. Historical logs are not rewritten;
an early-stopped path needs a new run to exercise its remaining turns.

## Safety

Never commit `.env`, credentials, cookies or internal wiki snapshots.
The agent must not inspect `.env`; helpers load authentication locally.
Before sharing this repository, inspect its Git history: early commits contained
internal snapshots. A local path-history check still finds those paths in commits `ec2e9cd`
and `a2af88a`; ignoring/deleting current snapshots does not remove historical content.
The source README and curated guidance also contain internal references. This is not a completed
content/secret audit or approval to publish: choose an approved internal audience, or prepare a
separately reviewed sanitized export without the old history. Do not rewrite history automatically.
The agent never submits access requests or runs load against
TEST/PROD on the user's behalf.

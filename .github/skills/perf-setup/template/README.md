# __PROJECT_NAME__

Gatling + Kotlin performance-test project (Java 17, Maven Wrapper).

At scaffold time, new projects contain shared infrastructure, the coding agent and infrastructure
unit tests only. Adding the first requested domain creates its layers and simulation, adds endpoint
keys to the initially empty env files, and adds a row below the `ci/simulation-data.csv` header.
Creating `orders` does not create `items`.
The optional `--demo` scaffold adds an explicit items example; only that mode includes the demo
CSV, simulation, `WeightSumTest`, HTTP fixtures/checker and manual demo HTTP workflow.

## Quick start
```bash
./mvnw -q test detekt:check
```
These commands compile code, run unit tests and perform static analysis. They do not execute
scenario HTTP requests or establish endpoint correctness; Maven may download dependencies.

### Source structure versus build output
Domain code follows `src/main/kotlin/cz/example/perf/domain/<domain>/` with the
`data`, `requests`, `steps`, `flows` and `usecases` layers. Its simulation belongs under
`src/main/kotlin/cz/example/perf/simulations/domain/<domain>/`; its unit tests and dummy CSV belong
under `src/test/kotlin/.../domain/<domain>/` and `src/test/resources/<domain>/`.
These domain directories appear when the first requested domain is generated, not at project creation.
The generator also creates `docs/<domain>.md` and exact default use-case name/weight assertions.

Maven creates `target/` locally for compiled classes, generated `Paths.kt`, test results and reports.
It is build output, not another source layer or domain. It is excluded by `.gitignore`, so it normally
does not appear when viewing an example repository on GitHub. The scaffold never copies a template's
old `target/`; running build checks creates a fresh one. Do not edit or commit generated files there.

## Add domains, endpoints or tests
Start the guided conversation in this repository:
```bash
copilot --agent perf-coding --model gpt-6-astra -i "Start"
```
The agent first asks whether to create a new domain or add/change tests in an existing one,
then collects the needed details one question at a time. It does not start with a repository audit.
`-i` sends the first message automatically; without it the CLI waits for you to type `Start`.
Do not use `/init` for this workflow: it generates repository instructions instead.
For a concrete task, replace `Start` with that request, or send it in an already open session.

### Optional helper approvals
To avoid repeated approvals for local task bookkeeping and domain generation, explicitly use:
```bash
python3 .github/scripts/start_coding.py
# Resume through the session picker, or supply the exact session ID:
python3 .github/scripts/start_coding.py --resume
python3 .github/scripts/start_coding.py --resume YOUR_SESSION_ID
```
This launcher starts in this repository, even when called from another directory. A new interview
receives `Start`; `--prompt "Your request"` changes that first message. Resuming does not send `Start`.
It grants four session-scoped CLI command-prefix permissions: `python` and `python3` for
`.github/scripts/task_state.py` and `.github/scripts/new_domain.py`, including their arguments.
Only run it if you trust those local scripts. This is not a Python sandbox: modifying those scripts
changes what an approved command can do. Alternate spellings/absolute paths may still prompt.
No general Python, shell, write, path or URL bypass is added; existing user/organization CLI
permissions still apply. It does not override a previously enabled allow-all mode.
The scripts may write task records or generate files; request approval and independent review
still belong to the agent workflow. HTTP traffic needs separate explicit approval.
Nothing is stored as an auto-approval in `.agent.md` or global configuration.
The direct CLI launch above remains available with its normal permission prompts.

Endpoint intake asks for path, missing HTTP method and expected status, then only applicable
parameters. It distinguishes gateway routing, public resources and availability checks from
payload formats such as JSON, form or multipart; it does not require a business interview.
HEAD/no-content and text/binary responses use appropriate checks, not default JSON assertions.
The agent gathers these contracts; the generator itself still provides GET/POST skeletons only.

Example requests (synthetic data only):
- "Help me create a load test, one step at a time." The agent asks whether to create a new domain
  or extend an existing one, then guides domain selection, API contract, data and mix decisions.
  You do not need to write a complete specification first. It confirms the assembled change
  before implementing; supplied facts are not asked again.
- "Add a demo orders domain: GET /orders, expected status 200, one use case at 100%. Run unit tests only."
- If items already exists (for example, in a demo): "In items, add GET /items/#{itemId}, expected status 200,
  using dummy IDs. Keep the current browse flow."
- With an existing domain: "Add a detail journey to orders and use a 70% browse / 30% detail mix.
  Test the exact names and weights."
- "Add unit tests for the existing orders mix without adding endpoints or running a simulation."

The agent asks for missing details one at a time, delegates implementation and obtains an independent
review. New domains use `new_domain.py`; existing domains are extended without regenerating their files.
Changes to this template are not automatically installed in previously created repositories.

### Bounded implementation and review
Astra remains the orchestrator and makes the final acceptance decision. It selects workers by task:
GPT-5.4 mini is the default for routine coding/mechanical review, while complex or uncertain work
can use Astra. Explicit user choices take precedence; the harness must support the selected model.
For a routine successful change, the coder runs one baseline
and one combined final check; one independent reviewer inspects the change and repeats the combined
check. Corrections still require affected checks. Baseline and pre-existing-edit evidence travel
with the handoff instead of being rediscovered in chat history. Existing test helpers are reused.

Keep approval prompts enabled. Tool timers include time waiting for permission, not just execution;
do not interpret that waiting as model computation or disable safeguards to hide it.

### Persistent task state
Coding tasks can be resumed from `.perf-coding/tasks/<task-id>.json`, which is local and gitignored.
The orchestrator may invoke `python .github/scripts/task_state.py ...` for bookkeeping only;
source edits and check execution remain worker responsibilities. If you prohibit all commands or
file changes, the discussion remains transient rather than being silently saved.

The record separates missing/provided facts, user approval, coder reports, independent review and
acceptance. Contract corrections revoke approval; changed build inputs invalidate old check evidence.
Build success cannot replace a review of every acceptance criterion. The helper stores reported
evidence, not authenticated execution proof, and does not provide technical role isolation.
Approval captures the pre-edit fingerprint; a baseline recorded after code changes is rejected.
The generator uses `--task <task-id>` during agent work and requires that passing baseline before
preview/generation. Direct manual generation without an active task still works.
For the record schema and resume/decision commands, see
[task-state.md](.github/skills/perf-coding/task-state.md). This first version handles code-only tasks;
local HTTP execution still requires separate approval. Existing projects are not automatically updated.

## Before a shared-environment run
Ask `perf-coding` for the TEST/PRED or PROD readiness checklist, including what still differs from
the mock. It reports known, user-confirmed, pending and unknown items without running traffic.
See [run-readiness.md](.github/skills/perf-coding/run-readiness.md) for environment configuration,
input-data replacement/injection, applicable authentication, permissions, runner connectivity,
approved limits and operational controls. Secret values and real client records stay out of chat/Git.
The scaffold does not include a TEST/PROD execution pipeline: `PRCheck` builds/checks code, while
the optional `DemoHttp` workflow uses only loopback. A CI mapping row does not provision a runner
or a performance workflow. A launch from a laptop to TEST still needs real-environment readiness.
GEORGEPETE-specific token lifetimes, workflows and Change examples are references, not defaults
or current authorization for another project. The agent never starts or schedules shared-env traffic.

## Optional demo HTTP check (demo projects only)
The following checker, fixtures and items simulation exist only if the onboarding scaffold used
`--demo`. They are not commands for an infrastructure-only project. For a normal new project,
first add the requested domain and then separately agree any mock implementation and run limits.

In a demo project, this reproducible check starts and stops its own ephemeral mock:
```bash
python3 .github/scripts/check_items_http.py
# Optional: require deliberately broken contracts to fail in disposable copies.
python3 .github/scripts/check_items_http.py --check-detectors
```
Requires Python 3.10+ (standard library only) and the same Java/Maven prerequisites as the build.
The check launches 13 synthetic users, at most 15 seconds of simulation time, with exactly
27 expected requests to an owned `127.0.0.1` mock. Maven has a separate 240-second build/run timeout.
It exercises the real sample browse flow and test-only fixtures for JSON creation/correlation,
producer failure/missing ID, form and multipart encoding, PUT/PATCH/DELETE/HEAD/OPTIONS with no-content
responses, per-request API-key isolation, and polling success/three-attempt exhaustion/terminal failure.
The mock checks actual methods, paths, query, headers and bodies; unexpected follow-up requests fail.
Five deliberately failed HTTP checks are expected, so a passing suite does not mean zero KO requests.
Polling exhaustion must skip the result request. Results, wire-contract errors and Maven output are in
`target/items-http-contract/`. Detectors verify failure gates, ID checks, header isolation and poll bounds.
These fixtures verify sample behavior and HTTP patterns, not arbitrary agent-generated code or a live API.
Normal unit/static checks still send no scenario HTTP; `DemoHttp.yml` requires manual opt-in.

For the demo items domain, after a separately approved run against a mock you already own:
Only run against your own local mock after confirming its address and supported routes:
```bash
./mvnw -q gatling:test -Dgatling.simulationClass=cz.example.perf.simulations.domain.items.ItemsMixSimulation \
  -DbaseUrl=http://127.0.0.1:8080 -DdurationSec=30 -DusersPerSecond=2
```
This assumes a mock serving `/items` on port 8080; the project does not start one for you.
If you have no mock, tell the agent. It can offer to create a synthetic one after your approval;
neither the example URL nor "sure" confirms a running server. Confirm the actual loopback address
and run limits before any probe or simulation.
Inspect the Gatling report and failed-request assertions. Do not target TEST/PROD.
`usersPerSecond` configures new virtual-user arrivals per second, not exact HTTP requests per second.
A journey with multiple requests produces different traffic from a single-request journey. Read measured
HTTP throughput in the Gatling report. The default is 2; values must be finite and greater than zero.
The deprecated `targetRps` property/environment variable and Kotlin property remain compatible aliases.
When both inputs are present, `usersPerSecond` takes precedence; invalid explicit input fails rather
than falling back to the alias or default.

Structure and conventions: `.github/copilot-instructions.md`.
Internal onboarding documentation (access, infrastructure): see the Confluence pages used by the `perf-setup` agent.

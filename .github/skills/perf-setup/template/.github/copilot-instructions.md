# Repository conventions - __PROJECT_NAME__

Read `.github/skills/perf-coding/rules.md` for shared safety and evidence boundaries.
Role policy lives in `.github/agents/perf-coding.agent.md`; do not duplicate it here.

## Commands (Java 17)
| Check | Command |
|---|---|
| Baseline unit tests | `./mvnw -q test` |
| Final unit and static checks | `./mvnw -q test detekt:check` |
| One existing unit-test class | `./mvnw -q -Dtest=<ExistingTestClass> test` |

The final command runs both goals in one Maven invocation. Maven may download dependencies.
HTTP execution is separate and subject to the shared runtime rules, not a prerequisite for coding.

## Layout and invariants
Under `src/main/kotlin/cz/example/perf/`:
- `domain/<domain>/{requests,steps,flows,usecases,data}` contains domain code.
- `simulations/domain/<domain>/<Domain>MixSimulation.kt` owns a domain simulation.
- `setup/` contains `UseCase`, weighted `MixBuilder` and arrival/assertion `SimulationSetup`.
- `config/` contains `Config`, `Env`, `Protocols` and generated `Paths`; `auth/` prepares authentication.

Layer order: requests, steps, flows, usecases, simulation. Simulations do not call Requests directly.
`Config` resolves JVM properties before same-named environment variables.
Inspect `Config` and `SimulationSetup` for supported arrival-rate inputs; older repositories may expose
only `targetRps`, newer ones `usersPerSecond`. `constantUsersPerSec` is user arrivals, not HTTP RPS.
New projects contain shared infrastructure only; no domain or HTTP fixture is created by default.
The optional `--demo` scaffold includes items and test-only HTTP fixtures, not additional real domains.
An absent domain directory before the first domain is normal; do not create items to fill it.
Paths come from both env files, `src/main/resources/env/{test,prod}.properties`, with identical key
sets. Do not edit generated `Paths.kt` under `target/generated-sources/paths`.
Feeder fixtures live in `src/test/resources/<domain>/<domain>.csv`.

File/package/class/CI selectors must agree for each simulation. `ci/simulation-data.csv` lists
`simulation,source,target`; reuse its row unless a new simulation is actually needed.
Register a new use case in `all`, confirm its weight, and keep unique names and finite non-negative
weights summing to 100. Tests must assert exact expected names and weights, not only their sum.
Generated domains use `<Domain>UseCasesTest`. Only the optional items demo uses `WeightSumTest`.
New scaffolds include `MixBuilderTest` for infrastructure without adding a domain; older checkouts
may have only `WeightSumTest`. Select an actual existing class before a focused test invocation.
Call `GatlingTestBootstrap.init()` before constructing Gatling DSL objects in unit tests.

## Agent entry
`copilot --agent perf-coding --model gpt-6-astra -i "Start"`

`-i` sends the first message; without it, type `Start`. `/init` generates repository instructions,
not the domain/test interview. The guide selects the implementation path; `endpoint-contracts.md`
selects conditional technical questions. `.perf-coding/tasks/` contains ignored local task records.

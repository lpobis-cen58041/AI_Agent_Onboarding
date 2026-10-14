# Copilot Instructions — __PROJECT_NAME__ (Gatling + Kotlin)

## Commands
```bash
./mvnw -q test-compile          # PR gate
./mvnw test                     # unit tests
./mvnw -q gatling:test -Dgatling.simulationClass="cz.example.perf.simulations.domain.items.ItemsMixSimulation" \
  -DbaseUrl="<BASE_URL>" -DdurationSec=30 -DtargetRps=2
```

## Architecture (domain-based)
Under `src/main/kotlin/cz/example/perf/`:
- `domain/<domain>/{requests,steps,flows,usecases,data}` — everything for one business domain
- `simulations/domain/<domain>/<Domain>MixSimulation.kt` — Gatling simulation per domain
- `setup/` (`UseCase`, `MixBuilder`, `SimulationSetup`), `config/` (`Config`, `Env`, `Protocols`), `auth/`

Layer order: requests → steps → flows → usecases → simulation. Never call requests from a simulation.

Resources: `src/main/resources/env/{test,prod}.properties` hold endpoint paths (identical key sets;
`config/Paths.kt` is generated from them at build time — do not edit). Tests mirror the main layout;
dummy feeder CSVs live in `src/test/resources/<domain>/<domain>.csv`.

## Conventions
- File path, package, class name of a simulation (and the workflow selector, when added) must match.
- Use case weights per mix sum to 100 (checked by `WeightSumTest`; add each domain there).
- Real feeder data is not committed; `ci/simulation-data.csv` (`simulation,source,target`) lists where CI
  downloads it. Add a row for every new simulation/domain.
- Use dummy tokens only; never commit real tokens, keys or internal URLs.

## Adding a new domain
1. Create `domain/<domain>/{requests,steps,flows,usecases,data}` and a dummy CSV in `src/test/resources/<domain>/`.
2. Add endpoint keys to BOTH `env/test.properties` and `env/prod.properties`.
3. Add `simulations/domain/<domain>/<Domain>MixSimulation.kt` and a row in `ci/simulation-data.csv`.
4. Extend `WeightSumTest`; run `./mvnw -q test-compile` and `./mvnw test`.

# Copilot Instructions — __PROJECT_NAME__ (Gatling + Kotlin)

## Commands
```bash
./mvnw -q test-compile          # PR gate
./mvnw test                     # unit tests
./mvnw -q gatling:test -Dgatling.simulationClass="cz.example.perf.simulations.SampleSimulation" \
  -DbaseUrl="<BASE_URL>" -DdurationSec=30 -DtargetRps=2
```

## Architecture
Layers under `src/main/kotlin/<base package>/`:
`requests/` (raw HTTP calls) → `steps/` (feeders, session) → `flows/` (composed chains) →
`usecases/` (weighted `UseCase`) → `simulations/` (Gatling `Simulation`).
Never call requests directly from a simulation.

## Conventions
- File path, package and class name of a simulation must match.
- Feeder CSVs with real data are not committed; `ci/simulation-data.csv` lists where CI downloads them
  (`simulation,source,target`).
- Use dummy tokens only; never commit real tokens, keys or internal URLs.

## Adding a new simulation
1. Add requests, steps, flows, use cases (weights sum to 100).
2. Add the simulation class and a data row in `ci/simulation-data.csv`.
3. Extend `WeightSumTest` and run `./mvnw -q test-compile` and `./mvnw test`.

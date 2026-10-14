# __PROJECT_NAME__

Sample Gatling + Kotlin performance-test project (Java 17, Maven Wrapper).

## Quick start
```bash
./mvnw -q test-compile
./mvnw test
./mvnw -q gatling:test -Dgatling.simulationClass=cz.example.perf.simulations.SampleSimulation \
  -DbaseUrl=<BASE_URL> -DdurationSec=30 -DtargetRps=2
```

Structure and conventions: `.github/copilot-instructions.md`.
Internal onboarding documentation (access, infrastructure): see the Confluence pages used by the `perf-setup` agent.

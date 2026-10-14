# Local dummy feeder data

CSV files here are artificial local data so that `./mvnw test` and local smoke runs work without
access to Artifactory. In CI, the data prepare step replaces them with real data for the domains mapped
to the simulation in `ci/simulation-data.csv`. Add a row there for every simulation / domain you add.

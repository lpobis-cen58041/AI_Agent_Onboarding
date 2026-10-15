# Guide: a new domain + tests (for a complete beginner)

Goal: the user adds one new domain to this repository and understands every file that was created.
Do not assume knowledge of Kotlin or Gatling. Explain one step at a time, in one sentence, with an everyday analogy.

## Mental model (layers)
A domain = one area of the service (e.g. `orders`). Each layer builds on the previous one:
1. **requests** - one API call ("call /orders and expect 200"). Like one click.
2. **steps** - preparation before a call (take a row from the CSV, set the token). Like "log in".
3. **flows** - the order of steps and calls. Like one whole user journey.
4. **usecases** - a flow + a weight (what % of the load it makes up). Weights in a mix add up to 100.
5. **simulation** - combines the use cases and runs them. Only via `*MixSimulation`; a request is never called directly from a simulation.
Data (**data**) = a feeder, a CSV with test inputs. Endpoint paths = `env/test.properties` and `env/prod.properties` (same keys in both).

## Procedure with the user
1. **Find out:** the domain name (lowercase letters/digits, e.g. `orders`), the endpoint path (e.g. `/orders`), the method (GET/POST).
   If they do not know the endpoint, use an invented path; never write real internal URLs or data.
2. **Check the repo:** `./mvnw -q test` must pass before any change.
3. **Preview:** `python .github/scripts/new_domain.py . <domain> --path <path> --method <GET|POST> --dry-run`, explain the list of files.
4. **Create:** the same command without `--dry-run`. The script creates only new files, adds a key to both `env/*.properties` and a row to `ci/simulation-data.csv`.
5. **Walk through the files by layer** (requests → steps → flows → usecases → simulation → test) and say what each is for.
6. **Run the tests:** `./mvnw -q test` (fast, no network). Explain the output. `<Domain>UseCasesTest` checks that weights add up to 100 and names are unique; `EnvPathsTest` checks equal keys in test/prod.
7. **Customize (one thing at a time, tests again after each):**
   - more calls in a flow: add another method in `Requests` and chain it in `Flows` (`.exec(...)`, `.pause(1)` for waiting),
   - another use case: add it to `UseCases` and to `all`, adjust weights so they add up to 100,
   - POST body: in `Requests` replace `StringBody("{}")` and add a `check(...)` on the response,
   - a new CSV column: add it to `src/test/resources/<domain>/<domain>.csv` (invented values only), use `#{column}` in the path/body.
8. **Static check:** `./mvnw detekt:check`.
9. **Local smoke run (optional):** only against the user's own local mock, command per `README.md` with the name of the new `*MixSimulation`. Never against TEST/PROD.
10. **Summary and next step:** what was created, what they learned, what remains (real data from Artifactory, review, PR). Commit/PR only on their request.

## Common errors (help diagnose)
- `Unresolved reference: <key>` - the key is missing in `env/test.properties` (`Paths.kt` is generated from it at build time).
- `EnvPathsTest` fails - the key is in only one of the `test`/`prod` files.
- `...UseCasesTest` fails on the sum - weights do not add up to 100.
- An error in `csv(...)` in a test - the file `src/test/resources/<domain>/<domain>.csv` is missing or the test does not call `GatlingTestBootstrap.init()`.
- `./mvnw` says `Permission denied` - `chmod +x mvnw`.
- A Java version error - Java 17 is required.

## Rules
- Dummy data only (`local-dummy-*`); no real tokens, URLs or data.
- Do not paste big blocks of code at once; prefer a small change, a test, an explanation.

# Glossary (for non-technical onboarding)

General explanations of terms. Always confirm internal specifics (who, when, limits) from the wiki snapshots.

- **Load / perf test:** deliberately loading a system with many simulated users to find out whether it handles real or higher traffic.
- **Simulation:** a runnable test (Gatling) describing what virtual users do and how fast.
- **Scenario / use case:** one type of user behavior (e.g. "show the list"); a simulation combines them.
- **Mix:** the ratio in which scenarios run (weights add up to 100 %).
- **RPS (requests per second):** how many requests per second the test generates.
- **Throttle:** limiting the speed so the test does not exceed the chosen RPS.
- **Ramp:** gradually increasing the load to the target value.
- **Stress test:** loading above the normal level to find the system's limit.
- **Assertion:** a success condition of a run (e.g. max % of errors, p95 response time below a limit).
- **p90 / p95 / p99:** the response time that 90 / 95 / 99 % of requests do not exceed.
- **Feeder:** a source of test data (CSV with tokens/accounts) from which virtual users take their inputs.
- **TEST / PROD:** the test environment / live traffic. PROD tests are risky and require approval.
- **PETE:** the team/platform for performance testing; it runs the infrastructure and the rules for runs.
- **Redim:** the access management system (access groups).
- **ServiceNow:** the system for submitting requests (access, SaaS, software).
- **Artifactory:** the artifact store; CI downloads test data and packages from it.
- **Runner:** the machine CI (GitHub Actions) runs on, including the load test.
- **CI / PR check:** automatic code check on a pull request.

# Guide: intake and implementation paths

Use the repository conventions for layout/commands, shared rules for safety, and role playbooks for
execution/review. Explain unfamiliar Kotlin/Gatling concepts only when needed.

## Guided conversation
Ask one missing decision, then wait; skip everything already supplied or discoverable in the repo.
No mandatory business interview, execution target, credentials, arrival rate or duration for coding.
The state helper in `task-state.md` records permitted interviews and returns the next question.
If the user prohibits commands/files entirely, keep transient state without pretending it was saved.

### Domain mismatch replies
Resolve these before planning an implementation. Use `ask_user` when available, with the matching
question below, substituting the user's domain and endpoint. In a text-only harness, ask it directly:
- Unknown existing domain: "Which repository contains `reports`, or which existing domain should
  receive `GET /reports`?" Keep creation blocked.
- Colliding new name: "Would you like to extend the existing `items` domain, choose a different
  name, or stop?" Do not regenerate it.
Do not replace the question with a third-person description of the next step. A command/edit prohibition
does not prohibit asking the user; these questions are not requests for permission to run commands.

### Normal intake
1. **New or existing:** ask new versus existing domain. This first choice needs no repository scan and
   must not also request a new domain name.
2. **Domain:** ask a new name, or offer actual existing domains from `domain/`. An unknown existing
   domain is not permission to create it.
   If the requested mode conflicts with the repository (unknown existing domain or colliding new
   name), stop and ask one explicit question to resolve the repository/domain choice; do not merely
   list options or silently switch modes.
   Use the domain mismatch replies above, even if the user asks for the safe next step.
3. **Change:** go directly to the endpoint for API work. If "test" is ambiguous, clarify Gatling
   journey versus unit test; a known Gatling goal does not need this question.
4. **Call contract:** ask the relative endpoint path, then the HTTP method, then the expected
   HTTP status. Accept combined answers without repeating fields. Read a supplied sanitized API
   specification rather than asking for facts it already contains.
5. **Relevant details only:** follow `endpoint-contracts.md`. Populate known facts and their sources,
   add unknown contract-specific fields, and mark genuinely inapplicable fields with a reason.
6. **Journey and mix:** collect real order/data dependencies and agreed weights only when applicable.
   A request-only change or unit-test change need not alter the mix. Do not invent a traffic split.
7. **Confirm:** summarize the agreed immediate change in at most 80 words, including
   "Shall I implement this change and run unit tests and static checks only?"
   Completing the parameters does not answer this separate approval decision.

Distinguish waiting for approval from a plan-only request. "No commands/edits during intake" keeps
execution blocked; an explicit "leave it as a plan", refusal or stop ends the interview without an
approval question. Record that hold when persistence is allowed. A negative answer or requested
correction must not start implementation; a corrected contract needs fresh approval.
During an active interview, a contract correction with "still don't execute or modify anything"
keeps implementation blocked but does not by itself end intake. Summarize the corrected contract
and ask the confirmation question from step 7 again; do not end with only "implementation is on hold".
An explicit "leave it as a plan", refusal or stop still ends the interview without another approval question.
A complete explicit implementation request can supply approval directly, scoped to its actual
instructions. Explanations/plans remain read-only; do not dispatch workers for an interview.

## Implementation paths
New projects start without domains. Generate only the requested domain, not an items example.
Domain and simulation directories are created by the generator as needed. Example assets are
included only in explicitly requested demo scaffolds; preserve them if they already exist.
Do not add an HTTP mock/contract fixture as an implicit part of creating a code-only domain.

| Request | Necessary change |
|---|---|
| New business domain | Confirm no collision, preview `.github/scripts/new_domain.py` with `--dry-run`, then generate all layers, simulation, dummy CSV, env keys, CI row and per-domain test. |
| Another endpoint | Extend existing Requests and only needed data/preparation; no regeneration. |
| New journey | Compose requests/steps in a flow and register its weighted use case. |
| Change the mix | Update agreed names/weights and their exact assertions; preserve injection. |
| Add or fix unit tests | Test the requested behavior without adding unrelated endpoints or domains. |

Use new_domain.py only for a new domain. Example:
`python .github/scripts/new_domain.py . orders --path /orders --method GET --task <task-id> --dry-run`.
Record the approved baseline before either invocation. An active task cannot omit `--task` or
generate against changed inputs. The generator also creates `docs/<domain>.md` and exact default-mix
assertions; adapt these when the agreed contract differs. Keep unrelated README content unchanged.
The generator supports GET/POST skeletons only; POST starts with `{}` and status 200. Adapt those
placeholders to the contract. For other methods/formats, start with a supported skeleton and adapt
the generated request, not unsupported flags. Retain both generator checks under `task-state.md`.
Use the generated `UseCasesTest`; do not duplicate it in `WeightSumTest`.
Do not assume every POST returns 200 or 201.

For existing endpoints, reuse feeder/auth preparation only when compatible with the contract.
Translate documented path placeholders to Gatling expressions such as `#{itemId}`; establish their
producer before use. Response correlation needs extraction and failure handling, not arbitrary CSV
substitution. New relative-path keys belong in both env files.
Preserve the existing simulation/CI row unless a separate mix is explicitly needed.

## Testing techniques
Reuse existing test helpers and public DSL APIs before inspecting dependency internals.
For pure validation, a small tested predicate wired into the real request check can avoid rebuilding
framework internals. Test actual types/boundaries; numeric conversion may silently truncate fractions.
Inspect only a concrete unresolved API using the resolved dependency version, and retain the result.
Constructing a Gatling chain is not HTTP execution. A short probabilistic mix cannot prove coverage
of every branch; approved mock contract checks need deterministic journeys, request counts and
failure/missing-data cases separate from production injection.

## Common errors
- Unresolved path key or `EnvPathsTest` failure: inspect matching env keys, not generated `Paths.kt`.
- Use-case test failure: check exact names, weights, uniqueness and total.
- CSV/Gatling unit initialization error: inspect the fixture and `GatlingTestBootstrap.init()`.
- Wrapper permission or Java error: workers check `mvnw` executable permission and Java 17.

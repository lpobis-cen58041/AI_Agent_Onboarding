# Run readiness: before TEST/PRED or PROD

Use this checklist for a requested shared-environment run or a question about what remains after
a mock pass, not for every coding task. It is guidance only: never start/schedule/approve traffic,
submit requests or automatically check permissions, tickets, credentials or connectivity.
Running from a client machine against TEST is not a mock run; the target, not the launch location,
determines the required data and authentication.

## How to present it
Aim for 120-150 words; the hard maximum is 180, including headings, status labels and table text.
Use exactly one opening sentence (at most 12 words), up to six rows (at most 12 words each),
and one priority sentence (at most 15 words). These budgets leave room for table formatting.
Use category-level phrases such as "TEST authentication and secret injection", not enumerations
of every unknown field. Mention each supplied fact/status once; do not repeat it in the priority.
Summarize each category, not every sub-bullet below; omit repeated disclaimers and any closing recap.
Those are the entire answer: do not append a reference catalog, source summaries or an actions-not-taken
paragraph. Include only decision-relevant reference facts inside a row, not the page descriptions below.
Do not list unrelated GEORGEPETE services for another project. For PROD, combine the additional controls
into those rows rather than adding a second full checklist.
Use `known` only for observed non-secret file facts; distinguish `user-confirmed`, `pending`,
`missing`, `unknown` and justified `not_applicable`. Unknown is not missing. Reuse confirmations and
pending requests without asking again. No automatic audit, worker dispatch or coding task record.
End with one priority unresolved item and its responsible team, not another full questionnaire.

Read only relevant non-secret source/configuration when permitted. For private data and credentials,
use metadata only: expected file/secret names, column schema, supplied row counts, provenance and
expiry confirmation. Do not open credential/customer-data files to complete the checklist.
Never ask for or print API key or token values, real identifiers or `.env` content.
A mock pass verifies only the exercised synthetic behavior, not readiness for a real environment.

## Before any shared-environment run (TEST/PRED and PROD)
1. **Scenario and target configuration:** identify the simulation, requested environment and actual
   config mapping. In this template only `test.properties` and `prod.properties` exist; do not invent
   a PRED mapping. Endpoint keys do not establish base URL, gateway routing or authentication.
   Treat localhost defaults and placeholders as unresolved real-target configuration.
2. **Input data:** identify each required feeder and schema, approved environment-valid test
   accounts/IDs, sufficient rows and dependencies. Approved synthetic TEST data may be valid;
   `local-dummy-*` fixtures are not evidence of that. Explain which fixtures must be replaced or
   injected and by whom, without copying real data into Git or chat.
3. **Authentication:** confirm the actual API profile, application identity, required API Manager
   publication/key or other auth, environment/audience, token lifetime/refresh and approved secret
   injection. Mark genuinely unused services not_applicable; do not prescribe Alfred or a token
   lifetime from another project. A personal permission is not an application key or run approval.
4. **Execution path and permissions:** identify CI versus an approved operator's machine, repository
   and workflow permissions, data/artifact permissions and runner network connectivity. Keep personal
   and runner/service-account rights separate. A shared-environment load workflow is not bundled:
   `PRCheck` runs unit/static checks; `DemoHttp` is loopback-only. A CI mapping row alone is not a
   working run pipeline. Use the project's real workflow inputs and report location, not guessed ones.
5. **Authorized load:** application-owner confirmation of scope, methods, concurrency/arrival rate,
   duration, window and stop thresholds. User arrivals are not exact HTTP requests per second.
6. **Observation and recovery:** agreed monitoring, stop operator, incident contact, results location,
   success criteria and cleanup/data effects. Unknown required controls keep readiness unconfirmed.

## Additionally for PROD
Require the team's current authorization/change process, permitted operations and side-effect
mitigations, execution window, monitoring and abort/escalation plan. Establish the applicable
Change type and approval state from current project evidence, not an old example. Never call an
unexecuted/failed test successful or treat repository permissions as permission to run PROD load.

## GEORGEPETE reference only
Apply these details only to confirmed GEORGEPETE work and distinguish reference guidance from
current readiness. Other projects must establish their own requirements.
- Confluence "How to run a simulation" (2318992641) describes CI token files in Artifactory,
  validity of 24 hours, renewal via Alfred (2017045811), workflow inputs and a ZIP report containing
  `reports/index.html`. Confirm the current mechanism/expiry; do not reuse these as universal defaults.
  Its local dummy-token example is not sufficient authentication for a shared TEST target.
- "How to add a scenario" (2318992259) points to environment-specific API publication/application
  keys and ApiMan training (1665533173); personal `APIMAN_DEVELOPER` permission is not the key.
- PETE production infrastructure (2134087447) describes dedicated API copies, scoped backends and
  GET-only methods unless alternatives are justified and mitigated. Confirm current allowed methods
  and business effects, not just the HTTP verb. Do not copy the reference schedule/load as approval.
- Change management (2304378840) discusses Normal Change but also contains open design questions
  and a possible Standard Change model. Confirm the team's current process; attach actual outcomes
  rather than treating the end of a scheduled window as success.
Internal source links remain in the onboarding repository's wiki snapshots.

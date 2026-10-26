# Endpoint-first contract intake

Collect the technical contract, not a business interview or a catalog of every possible test.
Ask one missing fact per turn. Accept combined answers and reuse supplied specifications and
compatible repository configuration. Read only the relevant sections; pass the agreed facts to
workers, not this entire checklist.

## Order and endpoint profiles
After the domain is known, ask for the relative endpoint path, then its HTTP method, then the
expected HTTP status code or explicitly allowed set. An answer such as "PATCH /items/{id}, 204"
already supplies all three. Do not infer a method or status from the path or from an example.
Expected HTTP status is separate from latency/throughput targets and authorization status.

Determine the applicable routing/authentication profile from the supplied contract or existing
compatible configuration. Ask about it only if the choice affects request construction and is
still unknown. These profiles are independent of HTTP method and payload format:

| Profile | Conditional information |
|---|---|
| Gateway / published API | Published relative path and selected route/channel if variants exist, existing protocol/header/auth profile. A web/mobile choice matters only when their contracts differ. Do not invent or double-prefix a gateway route. |
| Direct public resource | Confirmed unauthenticated contract, response format and meaningful response checks. "public" in a path is not proof that authentication is absent. Text or binary resources do not require JSON parsing. |
| Authorization-availability check | Agreed route and authentication profile, declared request fields and valid parameter combinations. This checks availability; it does not perform an actual authorization or transaction. |
| Other or unclear API | Ask for the missing technical contract. Do not force it into one of the above profiles or invent an integration. |

Reuse profile names/configuration, never request real API keys, tokens, identity values,
certificate contents or passwords. Preserve unrelated endpoints' routing/authentication.
The sample `Protocols.api` sends an API-key header and JSON Content-Type; it is not automatically
appropriate for an unauthenticated public resource or multipart request. A different contract
needs a scoped compatible profile/header setup, not a global removal of existing headers.
Code-only intake does not require a live base URL, credentials or an HTTP probe.

## Parameters needed for this call
Once method/path/status are known, collect only applicable missing details in this order:
1. Path variables: source of each value (fixed dummy value, feeder column or earlier response).
   For response-derived values, establish extraction and what happens when the producer fails or
   has no value. Do not silently substitute arbitrary feeder data.
2. Query parameters: declared names, required values and fixed versus variable inputs.
   Pagination/filter/sort parameters are relevant only if the contract uses them.
3. Request body: determine its format if unknown, then collect its declared fields.
4. Required request headers not already provided by the selected profile.
5. Response format and assertions beyond status, when wanted; any values needed by later calls.
Skip absent/already supplied fields. A method alone does not establish whether the API has a body,
which fields it requires or what status it returns.

| Request format | Ask for missing information only |
|---|---|
| No body | Path/query/header inputs only; do not add an empty JSON object automatically. |
| JSON | Sanitized example/schema, required fields/types, fixed values versus generated/feeder values. |
| Form URL-encoded | Form field names/values and variable sources; do not serialize it as JSON. |
| Multipart / file upload | Part names, dummy file source, media type and any declared accompanying fields. Never ask for a real customer file. |
| Other payload | Exact Content-Type and a sanitized contract/example before choosing serialization. |

For an availability contract that declares `identity.aliasType`, `identity.aliasValue`, `appId`,
`extTransactionId`, `transactionType` and `riskLevel.recommended`, establish their dummy data
sources and valid transaction-type/risk combinations. A fresh transaction ID may need generation
per request rather than a value reused for the whole run. Collect `transactionAmount` only if the
contract requires it; do not copy an example's amount, currency, risk level or identity into a
different request. Do not generate a Cartesian product of values without defined valid pairs.

## Response semantics
Support technical intake for GET, POST, PUT, PATCH, DELETE, HEAD and OPTIONS without assuming
that POST means creation, DELETE returns 204, or OPTIONS proves authorization.
HEAD responses and status 204 have no response body: use status and relevant headers, not JSON
body checks. For JSON/text/binary responses, select assertions matching the agreed format.
Status 202 proves acceptance, not asynchronous completion; gather polling/correlation and bounded
completion conditions only if completion checking is requested.

Do not turn negative/boundary variants into normal load traffic unless explicitly requested.
Conversation/approval belongs to `coding-guide.md` and `task-state.md`; generator limitations belong
to the implementation guide. Apply shared local-mock rules to any execution.

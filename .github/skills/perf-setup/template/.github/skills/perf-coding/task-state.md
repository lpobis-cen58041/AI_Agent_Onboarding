# Revisioned coding tasks

Canonical protocol for `.github/scripts/task_state.py`. Python's standard library is sufficient.
Records live in ignored `.perf-coding/tasks/<task-id>.json`; no secrets, raw customer data or internal
URLs. IDs are lowercase slugs. Records are local coordination data, not Git commits or migrations.
The helper changes only its state directory; it never executes a recorded command or edits code.
It fingerprints conventional build inputs plus README.md, docs and .gitignore, excluding `.env*`,
generated output and task state.

## Ownership and persistence
The orchestrator owns facts, intent, user decisions and final acceptance. The coder records baseline
and final implementation evidence. The reviewer returns structured evidence without writing records;
the orchestrator records that exact report with the reviewer's actual dispatch identifier.
These IDs associate reports with observed worker tasks; they do not authenticate an identity.

Use the helper instead of direct JSON edits. Every mutation after `init` requires the last returned
`--revision`; a stale writer fails without replacing data. Updates use a per-task lock and atomic
replacement. Do not retry a live writer or remove a lock until its owner has been checked.
A malformed/unavailable record is an explicit blocker, not grounds to proceed from memory.
If the user forbids all commands/files, retain transient discussion only and disclose that it is not
persistent. Do not dispatch an extra state worker or imply that a forbidden write occurred.

## Facts and next question
```bash
python .github/scripts/task_state.py init items-summary --data '{"goal":"Add an items summary request","intent":"interview"}'
python .github/scripts/task_state.py patch items-summary --revision 1 --data '{"domain_mode":{"value":"existing","source":"user"},"domain":{"value":"items","source":"user"},"change_type":{"value":"endpoint","source":"user"}}'
python .github/scripts/task_state.py show items-summary
```
Use the returned revision, not a number copied from this example. `show` returns facts, sources,
missing fields, `next_question`, phase, fingerprints, approvals and reports. Ask `next_question`
verbatim when input is required; do not replace it with "the next input is ...".

The initial `goal` is context; current sourced facts take precedence after a correction.
Core facts: `domain_mode` (new/existing), `domain`, `change_type` (endpoint/journey/mix/unit),
`acceptance` (criterion-ID to concrete description) and `preserve` (behavior descriptions).
Derive acceptance criteria from agreed request/mix facts, and preservation from the requested scope;
do not turn these into a business interview or repeat already answered questions.

Adding `endpoint.<name>.path` seeds that endpoint's missing `method`, `status` (list of codes),
`profile`, `path_parameters`, `query`, `body`, `headers` and `response`. Fill compatible repository
facts with their actual source. Values may be structured JSON: for example a body format/schema,
parameter bindings or response assertions. Do not mark an incomplete schema provided.
Use `detail.<name>` for additional contract-specific unknowns, with an explicit `question`.
`mix` maps exact use-case names to weights and is required for new domains, journeys and mix changes.

Each fact has status `unknown`, `provided` or `not_applicable`. Unknowns have no value/source.
Provided values need a source; an empty list means confirmed absence, not unknown.
Inapplicable optional fields need a source/reason and null value. Required identity/method/status
fields cannot be skipped this way. Use endpoint-contract guidance to establish completeness; the
helper validates record shape and common fields, not an arbitrary API's entire schema.
Batch supplied facts in one patch. The resulting question is the next turn; do not read `show`
again merely to obtain the revision you already received.

## Approval and lifecycle
`approve --data '{"source":"user: explicit code-only implementation approval"}'` binds approval to
the current complete contract revision and pre-edit code fingerprint. An explicit full implementation request can be its source;
the helper cannot infer or grant consent. `decline` uses the same source field and holds the task.
`intent --data '{"intent":"interview","source":"user: resume"}'` explicitly resumes a held task.
`plan_only` never authorizes implementation.

A changed fact revokes approval and final acceptance. Older reports remain in the record but cannot
satisfy a different contract revision. Corrections after a decline remain on hold until resumed.
Phases: `intake`, `awaiting_approval`, `on_hold`, `baseline`, `implement`, `review`,
`ready_to_accept`, `accepted`, `blocked`, `stale_code`.
The first version covers code-only changes; HTTP/run-only approval stays separate under shared rules.

## Evidence handoff
Use `report --revision N --data '<JSON>'` with:
```json
{
  "role": "coder",
  "worker_id": "actual-dispatch-identifier",
  "outcome": "pass",
  "summary": "Meaningful implemented change",
  "based_on": 1,
  "code_fingerprint": "fingerprint observed after checks, before further edits",
  "checks": [
    {"kind":"unit","command":"actual command","exit_code":0,"output":"actual relevant output"},
    {"kind":"static","command":"actual command","exit_code":0,"output":"actual relevant output"}
  ],
  "boundary": ["initial dirty paths/preserved behavior or focused changed-path evidence"],
  "unverified": ["HTTP behavior was not exercised"],
  "blockers": []
}
```
This is a schema example, not check evidence. A combined Maven invocation can support both check
entries; it must not be executed twice for those entries. Obtain the fingerprint with `show` around
the actual checks; if inputs change, rerun affected checks, never relabel old evidence.

`baseline` needs unit evidence and the initial dirty-worktree boundary before editing.
Recording it automatically retains a per-file `input_manifest` in the report; never supply or
rewrite that field. `show` returns `change_summary` (added/modified/deleted paths and unchanged count)
against that baseline even without Git. It covers the helper's documented input scope, not all files
on disk. Hashes prove unchanged content, not preservation within modified files; retain focused
before-edit snippets for those. A passing baseline cannot be replaced after edits. Older records
without a manifest return `change_summary: null`; do not reconstruct missing pre-edit evidence.
The first baseline must also match the approval fingerprint. Persist it before generation/edits;
do not delete/recreate work to hide an out-of-order implementation.
`coder` refers to its passing baseline report ID via `based_on`.
For a new domain, its passing `checks` must additionally include `generator-preview` followed by
`generator`, each with the actual command, exit code and create/append output. The preview command
must include `--dry-run`; generation uses the same arguments without that flag and the agreed domain.
Use these kind names, not `generation`, `preview` or `kind: static`; a narrative in `boundary` is
insufficient. For example, retain the observed output of
`python .github/scripts/new_domain.py . orders --path /orders --method GET --task <task-id> --dry-run` and then its
matching generation command. These checks are reported evidence, not proof authenticated by the helper.
Both commands require `--task` for an active approved coding task; the generator refuses a missing
baseline or changed inputs before writing anything. Direct standalone generation remains available
when there is no active task for that domain.
Preserve them through later corrections instead of rerunning creation to invent missing evidence.
`reviewer` refers to the current coder report ID and adds `criteria`, mapping EVERY acceptance ID to
`pass`, `fail` or `unverified`. A reviewer must differ from every coder on the task.
Reports retain observed failures as `fail`/`blocked`; never turn unavailable evidence into PASS.

### Read-only report validation
Before returning a reviewer report, run
`python .github/scripts/task_state.py validate-report <task-id> --revision N --data '<report JSON>'`.
This checks the same schema/evidence gates as `report`, without saving a report, changing the revision
or accepting the task. Use the current revision from `show`. A failed validation is an explicit error,
not permission to change evidence or mark an unverified criterion passed.

The reviewer JSON contains exactly these fields: `role` (`reviewer`), `worker_id`, `outcome`,
`summary`, `based_on` (current CODER report ID, not the baseline ID), `code_fingerprint`, `checks`,
`boundary`, `unverified`, `blockers`, and `criteria`. Put preservation findings in `boundary`, not a
separate `preservation` object. Do not add `coder_report_id`, `contract_revision`, `evidence` or `notes`.
Each check uses `kind`, `command`, `exit_code`, `output`; one observed combined command supports a
`unit` entry and a `static` entry. Return the validated JSON, not the validation result itself.
The coordinator must still use `report` to persist it; validation does not mutate the task.

Only after inspecting real reports and tool results may the orchestrator call
`accept --data '{"reason":"Assessment of criteria, preservation and independent evidence"}'`.
The helper requires current approval, passing baseline, coder and independent reviewer evidence,
successful unit/static checks, all criteria passed and an unchanged code fingerprint.
JSON metadata is not proof of execution or a sandbox. The orchestrator still evaluates the evidence;
successful bookkeeping must never replace that judgment.

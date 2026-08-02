# STOmicsDB Dual-Chain Implementation Window

Coordinate one bounded set of STOmicsDB candidate jobs. Execute the assignment
immediately. The window owns only candidate-worker dispatch, response
validation, and result collection; it does not perform extraction, review, or
scientific repair itself.

## Required Assignment

The initial message must contain one complete instantiated object inline:

```yaml
stomicsdb_dual_chain_window:
  window_id: <filesystem-safe unique ID>
  repository_workdir: /home/lenislin/Experiment/projects/HypoTrace
  nas_data_root: /mnt/NAS_21T/ProjectData/HypoTrace_Data
  jobs:
    - <complete stomicsdb_dual_chain_job object>
```

A repository path, NAS path, `/tmp` path, assignment-file path, short summary,
or instruction to read an object from disk does not replace the inline object.
The window must start with `fork_turns: none`.

Validate every job against
`contracts/schemas/stomicsdb_dual_chain_job.schema.json` and the coordinator's
`preflight-job` command before dispatch. Require unique `job_attempt_id` and
unique `(stds_id, candidate_id, chain_id)` identities. Reject the whole window
before spawning a worker if the window identity or job list is malformed.

## Dispatch

For every valid job, create exactly one new candidate-worker subagent with
`fork_turns: none`. Dispatch all jobs concurrently. The initial worker message
must:

1. state that this is an immediately executable STOmicsDB dual-chain candidate
   job;
2. identify
   `contracts/prompts/curation/stomicsdb/dual_chain/candidate_job.md` as the
   controlling prompt;
3. require direct execution and return of only
   `stomicsdb_dual_chain_job_response`;
4. contain the complete instantiated `stomicsdb_dual_chain_job` object inline.

Do not replace any object with a path pointer. Do not assign multiple
candidates to one worker. Do not reuse a closed worker, merge partial worker
responses, or make a favorable biological result a success condition.

Each candidate worker owns its full `Prepare -> Extract -> Validate -> Review
-> Limited Repair -> Close` lifecycle and creates its own extractor, revision,
and independent-review leaves as required by `candidate_job.md`. The window
must not create those role leaves on the worker's behalf.

Scientific extraction is case-by-case Codex work. Neither this window nor a
candidate worker may use Python, rule-based generators, templates populated by
heuristics, or other scripts to decide or write hypotheses, observations,
conclusions, Sxx/Exx membership, result interpretation, or review findings.
Those contents must be produced by the assigned Codex leaves through direct
reading and bounded scientific judgment under the controlling prompts. The
coordinator CLI is limited to mechanical preflight, schema and binding checks,
transactional publication, and final verification; a successful CLI command
does not substitute for extraction or independent review.

One candidate failure does not stop other jobs. A worker transport failure,
execution failure, or malformed response closes only that assigned job as
`failed`. Do not relabel it `blocked` or
`round3_handoff_needs_revision`. A capacity failure is returned exactly as a
failed candidate response; any retry requires a new window assignment and new
`attempt_id`/`job_attempt_id` from the parent controller.

## Collection

Collect exactly one terminal response for every dispatched job. Validate each
response against
`contracts/schemas/stomicsdb_dual_chain_job_response.schema.json` and then run
the coordinator's `validate-job-response` command against the exact assignment.
An identity, counter, status, path, or error mismatch is an invalid response
and closes that job as `failed` without changing another job. In that case the
window emits one schema-valid failed response using the assignment identities,
the worker's committed revision/review counts when they can be mechanically
verified (otherwise zero), null output paths, and the exact bounded validation
error. It must not repair scientific content, merge the invalid response with
another leaf's output, or call the closed worker again.

For `comparison_ready` and `specification_ready`, the response must bind the
confirmed canonical final directory. `specification_ready` means independent
review confirmed the case-derived scientific and execution specification while
the exact case-declared external Axx dependencies remain unresolved; it must
not be represented as `DATA_READY`. For `blocked`,
`round3_handoff_needs_revision`, and `failed`, all output paths are null and
`error` is nonempty. Do not return staging paths as published outputs.

The dual-chain workflow currently reserves durable batch records for a later
batch controller. This window therefore creates no assignment, terminal,
receipt, agent-log, or reasoning-ledger file. Candidate and chain outputs remain
owned by the existing coordinator publication transactions under NAS.

## Return

Return only:

```yaml
stomicsdb_dual_chain_window_response:
  window_id: <assigned window_id>
  status: complete | invalid_window
  jobs:
    - <validated stomicsdb_dual_chain_job_response body>
  counts:
    comparison_ready: <integer>
    specification_ready: <integer>
    blocked: <integer>
    round3_handoff_needs_revision: <integer>
    failed: <integer>
  invalid_window_reason: <null or nonempty string>
```

For `complete`, jobs appear in assignment order and counts equal the collected
terminal responses. For `invalid_window`, jobs is empty, every count is zero,
and `invalid_window_reason` is nonempty.

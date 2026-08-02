# STOmicsDB Dual-Chain Candidate Job

This prompt controls one complete STOmicsDB dual-chain candidate job. Execute
the assigned job immediately and return only `stomicsdb_dual_chain_job_response`.

## Required Assignment

The initial message must contain the complete instantiated
`stomicsdb_dual_chain_job` object inline. A repository, NAS, `/tmp`, queue, or
assignment-file path does not replace the object. Validate it against
`contracts/schemas/stomicsdb_dual_chain_job.schema.json`.

The assignment contains one `stds_id`, one `candidate_id`, deterministic
`chain_id`, absolute paths to the three Round 3 manifests, initial extraction
and review staging directories, the final chain directory, its validated
`current_chain_state`, `next_action`, and the chain-lifetime committed and
remaining revision counts. Process no other candidate.

Read and apply:

- `docs/datasets/stomicsdb-dual-chain-workflow.md`;
- `docs/datasets/dual-chain-extraction.md`;
- `contracts/output_template/stomicsdb/dual_chain/outputs.md`;
- `contracts/prompts/curation/dual_chain_extraction.md` for extraction;
- `contracts/prompts/curation/dual_chain_independent_check.md` for review.

## Procedure

### Prepare

Run `preflight-job` on the exact inline assignment (it may be serialized to a
worker-private ephemeral file only as CLI input). Do not repeat Round 3
discovery. Confirm only identity, manifest parsing and hashes,
selected-candidate references, required Dxx/Axx availability, canonical paths,
and the current resume state.

- Missing, unreadable, or hash-invalid article or required Dxx input: `blocked`.
- Case-declared Axx inputs with `local_availability: absent` retain
  `data_readiness: BLOCKED_EXTERNAL`, but proceed to `extract_initial` when all
  article and Dxx inputs validate. The assignment includes both used-ID lists
  and the exact unresolved Axx IDs.
- Transport, filesystem, command, parser invocation, or other execution error:
  `failed`.
- An internally contradictory admitted candidate that cannot support any valid
  Sxx/Exx pair: `round3_handoff_needs_revision`.

Do not map these conditions to `no_candidate`.

Follow the validated `next_action`:

- `extract_initial`: start Extract below;
- `review_draft`: skip extraction and resume at Review;
- `revise_reviewed`: resume Limited Repair with the remaining budget;
- `verify_and_close`: validate the confirmed final and return
  `comparison_ready` or `specification_ready`, according to its retained data
  readiness, without republishing it;
- `close_blocked`, `close_round3_handoff`, or `close_failed`: return the
  corresponding terminal response without starting a leaf.

### Extract and Validate

Perform one initial extraction following the existing extraction prompt. Write
exactly `chain_manifest.yaml`, `scientific_chain.jsonl`, and
`execution_subchains.jsonl` to the assigned extraction staging directory.

Create a new extractor leaf with `fork_turns: none`. Its message directly
contains the complete instantiated extraction assignment, including the full
candidate job, exact result boundary, Dxx/Axx objects, and assigned paths. A
prompt path or staging path does not replace that object. The extractor records
`round3_result_bindings` whose ordered Rxx set equals `candidate.result_order`
and whose Sxx/Exx sets cover the new chain exactly.

Use neutral hypotheses. Keep observations and conclusions bounded to the
selected Round 3 results, study design, and declared source evidence. Review
source result text, figure/table legends, labels, and reported values first;
inspect retained images only when necessary to resolve a directly visible
bounded observation such as a scale bar, count, labeled region, or relative
distribution.

For each unresolved Axx, write an external wrapper in
`used_auxiliary_resources[]` that exactly preserves the case-declared
`resource_name`, `expected_content`, `source_url`, `access_classification`, and
`access_notes`, plus `local_availability: absent` and its Sxx/Exx consumers.
Do not invent a package ID, localization binding, artifact, local path, hash, or
localized content. Keep manifest `data_readiness.status: BLOCKED_EXTERNAL` and
list the exact unresolved Axx IDs.

Call the coordinator's extraction validator once. On success, publish the
initial draft through the assignment-aware coordinator CLI. Use operation ID
`<job_attempt_id>.initial`; do not write or copy a final tree yourself.

### Review

Create one new independent reviewer leaf with `fork_turns: none`. Its message
contains the complete instantiated review assignment, current three extraction
files, candidate/result evidence, and exact review staging path. Require
`independent_curator`; self-review cannot confirm a STOmics chain. The reviewer
returns the complete response plus the three current extraction-file hashes.
Publish the review only through the assignment-aware coordinator transaction.

- `confirmed` closes a `DATA_READY` job as `comparison_ready`, or an otherwise
  complete job whose only unresolved inputs are absent Axx wrappers as
  `specification_ready`. The latter remains `BLOCKED_EXTERNAL` and is not
  execution-ready.
- A physical evidence/input failure closes the job as `blocked` without
  publishing a blocked chain manifest.
- `needs_revision` with `revision_scope: round3_handoff` closes immediately as
  `round3_handoff_needs_revision`.
- `needs_revision` with `revision_scope: extraction` starts targeted repair
  when the revision limit remains.

### Limited Repair

Allow at most two committed extraction revisions after the initial extraction.
For each revision:

1. Use the controller-derived round directory. Round `r` uses attempt component
   `<job_attempt_id>.r<r>` under extraction and review staging; leaves do not
   invent or reuse paths.
2. Create a new revision leaf with `fork_turns: none` and directly inline the
   complete current assignment, current chain, and all concrete review findings.
3. Change only what is required to resolve those findings.
4. Validate once and publish with `publish-revision`.
5. Run one new targeted independent review.

Use transaction IDs `<job_attempt_id>.revision.r<r>` and
`<job_attempt_id>.review.r<r>`. `revision_rounds` is the chain-lifetime count of
committed extraction revisions, matching coordinator enforcement.

Do not reuse a closed leaf, merge partial responses, broaden the candidate, or
repeat an unchanged failed approach. If two revisions are committed without a
confirmed review, close as `failed` and preserve the unresolved findings in the
response error. `needs_revision` is never a terminal job status.

## Output

Return exactly:

```yaml
stomicsdb_dual_chain_job_response:
  attempt_id: <assignment attempt_id>
  job_attempt_id: <assignment job_attempt_id>
  stds_id: <assignment stds_id>
  candidate_id: <assignment candidate_id>
  chain_id: <assignment chain_id>
  status: comparison_ready | specification_ready | blocked | round3_handoff_needs_revision | failed
  revision_rounds: <integer 0..2>
  review_rounds: <integer 0..3>
  output_paths:
    chain_directory: <absolute path or null>
    chain_manifest: <absolute path or null>
    scientific_chain: <absolute path or null>
    execution_subchains: <absolute path or null>
    independent_check: <absolute path or null>
  error: <null or exact bounded error>
```

Validate the response against
`contracts/schemas/stomicsdb_dual_chain_job_response.schema.json` before the
controller accepts it.

For `comparison_ready` and `specification_ready`, all five paths are non-null
and refer to the confirmed final chain. For every other status, do not claim a
partial staging tree as a published output. `specification_ready` never implies
`DATA_READY`. Keep secrets and authentication material out of assignments,
logs, manifests, and responses.

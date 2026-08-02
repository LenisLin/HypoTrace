# STOmicsDB Dual-Chain Outputs

This contract defines the STOmicsDB candidate-job boundary. It reuses the
shared scientific and execution JSONL schemas and adds strict STOmicsDB-specific
chain-manifest, job-assignment, and terminal-response schemas.

## Job Assignment

`stomicsdb_dual_chain_job` is the full inline assignment returned by the
coordinator preflight and validated by
`contracts/schemas/stomicsdb_dual_chain_job.schema.json`.

```yaml
case_route: public_database_stomicsdb
attempt_id: <filesystem-safe batch/attempt ID>
job_attempt_id: <attempt_id>__<chain_id>
max_revision_rounds: 2
stds_id: STDS0000000
case_id: stomicsdb_STDS0000000
candidate_id: C01
chain_id: chain_sha256_0000000000000000
case_manifest_path: <absolute path>
source_manifest_path: <absolute path>
case_data_manifest_path: <absolute path>
extraction_staging_directory: <absolute path>
review_staging_directory: <absolute path>
final_chain_directory: <absolute path>
current_chain_state: absent | draft | needs_revision | comparison_ready | specification_ready | blocked
next_action: extract_initial | review_draft | revise_reviewed | verify_and_close | close_blocked | close_round3_handoff | close_failed
committed_revision_rounds: <integer 0..2>
remaining_revision_rounds: <integer 0..2>
input_binding:
  stds_id: STDS0000000
  candidate_id: C01
  case_manifest: {path: <NAS-relative path>, sha256: <64 lowercase hex>}
  source_manifest: {path: <NAS-relative path>, sha256: <64 lowercase hex>}
  case_data_manifest: {path: <NAS-relative path>, sha256: <64 lowercase hex>}
data_readiness: DATA_READY | BLOCKED_EXTERNAL
readiness_errors: []
used_data_object_ids: [D01]
used_auxiliary_resource_ids: [A01]
unresolved_auxiliary_resource_ids: [A01] # only for extractable BLOCKED_EXTERNAL
```

The two used-ID lists are present for `DATA_READY` assignments and for
`BLOCKED_EXTERNAL` assignments whose only unresolved inputs are case-declared
absent Axx resources. The latter also has a nonempty
`unresolved_auxiliary_resource_ids` list and proceeds to extraction. A physical
article or Dxx failure has neither used-ID list and closes as `blocked`.
Assignment files may be retained as batch bindings, but child-task transport
always contains the full object inline.

Round-zero staging paths are listed above. For round 1 or 2, replace the attempt
component with `<job_attempt_id>.r<round>`; the controller, not a leaf role,
derives the path.

## Extraction Output

An extraction attempt writes exactly three nonempty files:

```text
chain_manifest.yaml
scientific_chain.jsonl
execution_subchains.jsonl
```

- `chain_manifest.yaml` validates against
  `contracts/schemas/stomicsdb_dual_chain_manifest.schema.json` and the
  coordinator's cross-file/path/hash checks.
- Each nonempty line of `scientific_chain.jsonl` validates against
  `contracts/schemas/scientific_chain.schema.json`.
- Each nonempty line of `execution_subchains.jsonl` validates against
  `contracts/schemas/execution_subchains.schema.json`.

The manifest schema checks local shape. The coordinator remains authoritative
for deterministic IDs, bound hashes, candidate membership, Dxx/Axx subsets,
Sxx/Exx links, observation equality, object continuity, source-anchor scope,
and publication state.

Every new extraction/revision manifest includes `round3_result_bindings`. Its
ordered Rxx list equals candidate `result_order`, and its Sxx/Exx sets cover all
non-S00 scientific units and execution subchains exactly once. Existing
confirmed chains published before this field was introduced are accepted only
by the read-only final validator; any new revision must add the binding.

An unresolved Axx is represented by an external wrapper, not a localization
wrapper. It preserves the case-declared Axx ID, resource name, expected content,
source URL, access classification, access notes, `local_availability: absent`,
and Sxx/Exx consumers exactly. It contains no package ID, localization binding,
artifact reference, local path, or hash. Such a manifest retains
`data_readiness.status: BLOCKED_EXTERNAL` and lists its exact unresolved Axx IDs.

## Reviewed Output

A review attempt writes exactly:

```text
chain_manifest.yaml
independent_check.md
```

The coordinator combines those with the unchanged JSONL files in a recoverable
replacement transaction. A confirmed final chain contains exactly:

```text
chain_manifest.yaml
scientific_chain.jsonl
execution_subchains.jsonl
independent_check.md
```

The reviewer response also binds the raw-byte hashes of the three current
extraction files. Those hashes identify the inspected draft; they are not a
third review-staging file and do not require rehashing Dxx/Axx artifacts.

## Job Response

The wrapper validates against
`contracts/schemas/stomicsdb_dual_chain_job_response.schema.json`; the
coordinator then enforces assignment identity, counters, status/error rules,
canonical paths, and confirmed-final validity.

```yaml
stomicsdb_dual_chain_job_response:
  attempt_id:
  job_attempt_id:
  stds_id:
  candidate_id:
  chain_id:
  status: comparison_ready | specification_ready | blocked | round3_handoff_needs_revision | failed
  revision_rounds: 0
  review_rounds: 0
  output_paths:
    chain_directory:
    chain_manifest:
    scientific_chain:
    execution_subchains:
    independent_check:
  error:
```

`needs_revision` is an intermediate chain/review state and is never returned as
a closed job status. `review_rounds` counts valid review responses: one initial
review plus at most one review after each of two revisions. `revision_rounds`
is the chain-lifetime committed revision count returned by preflight and
publication transactions, not merely the count in the current process.

For `comparison_ready` and `specification_ready`, all five paths equal the
canonical confirmed final and `error` is null. For every other terminal status,
all five paths are null and `error` is a nonempty bounded explanation; staging
paths are never outputs.

## Status Semantics

- `comparison_ready`: validation and an issue-free independent review both
  passed, all inputs are `DATA_READY`, and the four-file final chain was
  atomically published.
- `specification_ready`: scientific extraction, validation, and issue-free
  independent review passed and the four-file final chain was atomically
  published, but one or more exact Axx wrappers remain externally unresolved;
  `data_readiness` therefore remains `BLOCKED_EXTERNAL`.
- `blocked`: the article or a required Dxx is absent, unreadable, or
  hash-invalid. This is not scientific ineligibility and does not publish a
  blocked chain directory.
- `round3_handoff_needs_revision`: the accepted Round 3 candidate is internally
  contradictory and cannot support a valid chain without changing Round 3.
- `failed`: execution, transport, filesystem, publication, validator, or
  exhausted-repair failure.

Null, negative, or non-significant source findings use the same engineering
success criteria as positive findings.

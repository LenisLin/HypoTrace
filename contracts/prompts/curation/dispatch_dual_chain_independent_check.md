# Dispatch: Dual-Chain Independent Check

This is a subagent entry for assigning one independent-check task. It is not
the stage protocol.

For `public_database_stomicsdb`, this is an internal leaf contract only. The
operator enters through the STOmics candidate controller, which creates a new
reviewer leaf with `fork_turns: none` and directly inlines the complete review
assignment. A prompt, queue, assignment, `/tmp`, or staging path never replaces
that object.

Stage: dual-chain independent confirmation.

## Required Inputs

Set `case_route: tool_method | public_database_stomicsdb`.

For `tool_method`, provide:

- `method_screening_yaml`
- `method_slug`
- `case_id`
- Per-case `case_screen.yaml`, `source_manifest.yaml`, and
  `case_data_manifest.yaml`
- Chain directory for one `chain_id` under
  `raw_data/tool_method/<method_slug>/cases/<case_id>/dual_chain/<chain_id>/`
- Unique absolute NAS review-attempt staging directory

For `public_database_stomicsdb`, provide instead `stds_id`, one `candidate_id`,
absolute paths to the canonical
`case_manifest.yaml`, `source_manifest.yaml`, and
`data/case_data_manifest.yaml`, and the chain directory under
`raw_data/public_database/stomicsdb/cases/<case_id>/dual_chain/<chain_id>/`.
Also provide the deterministic `chain_id`, the absolute extraction-attempt
staging path bound by the queue row, and a unique absolute NAS review-attempt
staging directory.
Do not require `method_slug`, `screening.yaml`, or `case_screen.yaml`.
Derive `case_id` as `stomicsdb_<STDS_ID>`.

## Required References

Read these project documents before acting:

- `docs/datasets/tool-method-case-extraction.md`
- `docs/datasets/data-contract.md`
- `docs/datasets/dual-chain-extraction.md`

`docs/datasets/tool-method-case-extraction.md` is required only for
`case_route: tool_method`.

Use `docs/datasets/data-contract.md` Chain Data Object References when checking
`chain_manifest.yaml:used_data_objects`; it remains `Dxx`-only.
For public data, each `used_data_objects[].id` resolves to a Round 3
`data_objects[].data_id` in the candidate results'
`result_data_links[].data_inputs`. Every member result must declare the same
nonempty `primary_spatial` set and candidate `spatial_data_ids` must equal that
set exactly. Verify exact sample IDs and require every component path and
SHA-256 to be a subset match to the referenced `Dxx` component files.
Resolve every used `Axx` through
`chain_manifest.yaml:used_auxiliary_resources[]`. A localized entry is valid
only when its canonical package ID, exact package-manifest path and
raw-byte hash, package and generation IDs, artifact paths and hashes, and
complete expected-content coverage validate against a canonical manifest with
`auxiliary_localization_manifest.localization_status: LOCALIZED`.
The wrapper's `canonical_resource_id` and `package_id` must both equal the
localized package ID.

## Required Templates

Use these canonical templates:

- `docs/datasets/dual-chain-extraction.md` `chain_manifest.yaml` Template.
- `contracts/output_template/scientific_chain.jsonl`
- `contracts/output_template/execution_subchains.jsonl`

## Mandatory Stage Protocol

Follow `contracts/prompts/curation/dual_chain_independent_check.md`.

## Output Path

- In the specified review-attempt staging directory, write exactly two nonempty
  files: a proposed full `chain_manifest.yaml` and `independent_check.md`.
- Return `dual_chain_independent_check_response` with assignment identity, the
  staging path, and `reviewer_input_hashes` for the current draft
  `chain_manifest.yaml`, `scientific_chain.jsonl`, and
  `execution_subchains.jsonl`. These identify the inspected draft; do not
  rehash large Dxx/Axx artifacts.
- Never write the final chain directory.

Return exactly:

```yaml
dual_chain_independent_check_response:
  case_route: public_database_stomicsdb
  attempt_id: <candidate-job attempt_id>
  job_attempt_id: <candidate-job job_attempt_id>
  stds_id: <assigned stds_id>
  candidate_id: <assigned candidate_id>
  chain_id: <assigned chain_id>
  review_round: <0..2>
  review_staging_directory: <assigned absolute path>
  reviewer_input_hashes:
    chain_manifest.yaml: <64 lowercase hex>
    scientific_chain.jsonl: <64 lowercase hex>
    execution_subchains.jsonl: <64 lowercase hex>
```

## Boundary

Write the proposed review file and full manifest only. Do not write screening
outputs, localization outputs, new chain extraction artifacts, or edited JSONL
chain artifacts. The coordinator acquires the chain lock, reopens and verifies
the final/proposed files and unchanged JSONL hashes under that lock, and without
releasing it publishes the proposal through a recoverable
`PREPARED -> COMMITTED | ROLLED_BACK` per-chain replacement transaction with a
backup of the current final review-owned files.

Confirm case-derived execution from localized source material for both declared
granularities. Do not execute, replay, or regenerate the method. Check
source-observed `input -> call(parameters) -> output` continuity. An actually
absent, unreadable, or hash-mismatched bound input is a blocker. For public
data, available and hash-valid manifests whose declared path cannot support any
schema-valid HVU/E pair instead produce a Round 3 handoff `needs_revision`
finding. The candidate-job controller maps an unresolved handoff finding to
terminal `round3_handoff_needs_revision`; the reviewer does not write that job
status into `chain_manifest.yaml`.

Apply the Result Evidence Review Order from the mandatory Stage 4 protocol.
Judge source localization for support of the written observation, not for
complete collection of every available figure, rendered page, or generated
artifact.

Apply the neutral-hypothesis rule to every non-S00 HVU. A directional
hypothesis is a correctable extraction issue and should be recorded as
needs_revision.

Record correctable extraction and reference-expression issues only in the
proposed `independent_check.md` and
`chain_manifest.yaml:independent_check`; do not
modify JSONL chain artifacts during this stage.

The subagent handles only the specified `case_id` and chain directory. It
proposes only that chain's `independent_check.md` and full
`chain_manifest.yaml` in review staging.
For public data, verify the deterministic chain ID, three-manifest hash binding,
selected-candidate boundary, `1..n` schema-valid HVU/E pairs, and article-anchor
support through declared `source_anchors` figure, table, or stable text
locators. Confirm every exact required component path is readable and
hash-valid. Any required `Axx` with `local_availability: absent` prevents
`DATA_READY`; characterized external access alone is insufficient, and a
localized claim must pass the canonical binding checks above. Keep this
check lightweight: reopen only declared anchors and referenced components, do
not repeat Round 3 discovery, broaden the candidate, or infer missing
connections.

For a public STOmics queue, each row and fully instantiated assignment must
include `stds_id`, `candidate_id`, absolute paths to all three case manifests,
the deterministic `chain_id`, and absolute extraction staging, review staging,
and final chain paths.

A `needs_revision` result does not authorize JSONL edits. Extraction
replacement uses a new three-file staging attempt and a separate locked,
recoverable replacement transaction with a complete prior-chain backup; the
new manifest resets the check to `not_started`.

For STOmics, set `revision_scope: extraction | round3_handoff` whenever status
is `needs_revision`, require `independent_curator`, and record checked-data IDs
equal to the exact selected Dxx/Axx union. Physical input failure returns to the
candidate controller as `blocked` without publishing a blocked review tree.

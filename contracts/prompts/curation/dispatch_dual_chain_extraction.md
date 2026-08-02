# Dispatch: Dual-Chain Extraction

This is a subagent entry for assigning one dual-chain extraction task. It is
not the stage protocol.

For `public_database_stomicsdb`, this is an internal leaf contract only. The
operator enters through
`contracts/prompts/curation/stomicsdb/dual_chain/candidate_job.md`; the
candidate controller creates this leaf with `fork_turns: none` and directly
inlines the complete instantiated extraction assignment. A prompt, queue,
assignment, `/tmp`, or staging path never replaces that object.

Stage: dual-chain extraction.

## Required Inputs

Set `case_route: tool_method | public_database_stomicsdb`.

For `tool_method`, provide the existing inputs:

- `method_screening_yaml`
- `method_slug`
- `case_id`
- Per-case `case_screen.yaml`
- Per-case `source_manifest.yaml`
- Per-case `case_data_manifest.yaml` with
  `case_data_manifest.data_localization_status: DATA_READY`
- Coordinator-computed `chain_id`, unique absolute NAS extraction-attempt
  staging directory, and absent final chain directory under
  `raw_data/tool_method/<method_slug>/cases/<case_id>/dual_chain/<chain_id>/`

For `public_database_stomicsdb`, provide instead:

- `stds_id`
- one `candidate_id`
- absolute `case_manifest.yaml`, `source_manifest.yaml`, and
  `data/case_data_manifest.yaml` paths
- deterministic `chain_id`
- unique absolute NAS extraction-attempt staging directory
- reserved unique absolute NAS review-attempt staging directory
- absolute final chain directory under
  `raw_data/public_database/stomicsdb/cases/<case_id>/dual_chain/<chain_id>/`

For `public_database_stomicsdb`, provide `stds_id`, one `candidate_id`, absolute
paths to the three Round 3 manifests, and the target public-case chain
directory. Verify matching `stds_id` values and resolve the candidate's result,
data, auxiliary-resource, order, and connection references before extraction.
Restrict local objects to IDs in the candidate results'
`result_data_links[].data_inputs`; require every member result to declare the
same nonempty `primary_spatial` ID set and require `spatial_data_ids` to equal
that set exactly. Resolve each input's exact sample IDs and required component
paths; verify that every path and SHA-256 is a subset match to the referenced
`Dxx` component files. Record each used `Dxx` object by its Round 3 `data_id`
in `used_data_objects[]`. Record each used `Axx` separately in
`used_auxiliary_resources[]`.
This route does not require `method_slug`, `screening.yaml`, or
`case_screen.yaml`. Derive `case_id` as `stomicsdb_<STDS_ID>`. Assignment paths
are absolute; persist the three manifest paths in the chain binding as
NAS-data-root-relative values with their consumer-computed raw-byte SHA-256
values.

## Required References

Read these project documents before acting:

- `docs/datasets/tool-method-case-extraction.md`
- `docs/datasets/data-contract.md`
- `docs/datasets/dual-chain-extraction.md`

`docs/datasets/tool-method-case-extraction.md` is required only for
`case_route: tool_method`.

## Required Templates

Use these canonical templates:

- `docs/datasets/dual-chain-extraction.md` `chain_manifest.yaml` Template.
- `contracts/output_template/scientific_chain.jsonl`
- `contracts/output_template/execution_subchains.jsonl`

## Mandatory Stage Protocol

Follow `contracts/prompts/curation/dual_chain_extraction.md`.

## Output Paths

Write exactly these nonempty chain artifacts under the extraction-attempt
staging directory:

- `chain_manifest.yaml`
- `scientific_chain.jsonl`
- `execution_subchains.jsonl`

Never write the final chain directory. Return the staging path. The coordinator
validates the complete cross-file contract and all bound input hashes, acquires
the chain lock, confirms the final directory is absent, and publishes only by
same-filesystem atomic directory rename.

## Boundary

Write chain extraction outputs only. Independent confirmation is a later stage.
Do not alter localization outputs except to report blockers. A required `Axx`
with `local_availability: absent` blocks readiness. A localized `Axx` is valid
only when its package-manifest path and raw-byte hash, package and generation
IDs, required artifact paths and hashes, and complete
expected-content coverage all validate against a canonical manifest with
`auxiliary_localization_manifest.localization_status: LOCALIZED`. A URL,
download record, or staging artifact is insufficient. In the chain wrapper,
`canonical_resource_id` and `package_id` both equal that localized package ID.

The subagent must follow the HVU candidate check loop and the execution route
and subchain check in
`contracts/prompts/curation/dual_chain_extraction.md` before writing the staged
`scientific_chain.jsonl` and `execution_subchains.jsonl`.

The subagent handles only the specified `case_id`, candidate when applicable,
and extraction-attempt staging directory.
For public data, one candidate maps to one chain directory with `1..n` HVU/E
pairs; do not broaden the candidate, infer missing connections, or merge
candidates. Reopen only declared `source_anchors` figure, table, or stable text
locators and exact required component paths. A required `Axx` with
`local_availability: absent` prevents `DATA_READY`; characterized external
access alone is insufficient, and a localized claim must pass the canonical
binding checks above.
Contradictory Round 3 references or required component paths produce
`round3_handoff_needs_revision` at candidate-job closure, not downstream
scientific repair. `needs_revision` is reserved for an intermediate,
correctable drafted chain. Additional candidates require separate dispatch.

For a public STOmics queue, each row and the fully instantiated child assignment
must carry `stds_id`, `candidate_id`, the absolute paths of all three manifests,
the deterministic `chain_id`, and absolute extraction staging, review staging,
and final chain paths. Paths or queue-file pointers do not replace the inline
assignment.

Every new STOmics extraction or revision includes ordered
`round3_result_bindings` with exact Rxx, Sxx, and Exx coverage. Raw/input Dxx and
Axx objects establish execution availability, not new scientific observations;
observation support comes from admitted article anchors or an explicitly bound
precomputed Round 3 result object.

If a confirmed Stage 4 review requests extraction revision, dispatch a new
three-file attempt to new staging. The coordinator uses a locked recoverable
replacement transaction with a full backup and resets the independent check to
`not_started`; neither curator nor reviewer edits published JSONL in place.

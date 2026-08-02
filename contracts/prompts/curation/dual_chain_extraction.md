# Dual-Chain Extraction Curator Prompt

## Purpose

Use this internal prompt to construct case-derived dual-chain artifacts for
`case_route: tool_method | public_database_stomicsdb`. The output is
evaluator-facing curation material, not an agent-facing task prompt and not a
ground-truth trajectory.

## Inputs

For `case_route: tool_method`, use the existing inputs below:

- `method_screening_yaml`:
  `raw_data/tool_method/<method_slug>/screen/screening.yaml`.
- `method_slug`.
- `case_id`.
- `case_screen.yaml` from
  `raw_data/tool_method/<method_slug>/cases/<case_id>/case_screen.yaml`.
- `source_manifest.yaml` from
  `raw_data/tool_method/<method_slug>/cases/<case_id>/source_manifest.yaml`,
  with localized source material.
- `case_data_manifest.yaml` from
  `raw_data/tool_method/<method_slug>/cases/<case_id>/data/case_data_manifest.yaml`,
  with `case_data_manifest.data_localization_status: DATA_READY`.
- Localized source materials listed in `source_manifest.yaml`, such as source
  documents, source pages, tutorials, examples, vignettes, notebooks, scripts,
  code snapshots, and download logs when permitted by access and license
  constraints.
- Coordinator-computed `chain_id`, unique absolute NAS extraction-attempt
  staging directory, and absent final chain directory:
  `raw_data/tool_method/<method_slug>/cases/<case_id>/dual_chain/<chain_id>/`.

One invocation handles one specified `case_id`, one staging attempt, and one
final `dual_chain/<chain_id>/` directory.

For `case_route: public_database_stomicsdb`, use instead:

- `stds_id`.
- One `candidate_id`.
- Absolute canonical `case_manifest.yaml`, `source_manifest.yaml`, and
  `data/case_data_manifest.yaml` paths.
- Coordinator-computed deterministic `chain_id`.
- Unique absolute NAS extraction-attempt staging directory, reserved unique
  absolute NAS review-attempt staging directory, and absent final directory
  `raw_data/public_database/stomicsdb/cases/<case_id>/dual_chain/<chain_id>/`.

Do not require `method_slug`, `screening.yaml`, or `case_screen.yaml` for this
route. Derive `case_id` as `stomicsdb_<STDS_ID>`. Verify matching `stds_id`
values, the selected candidate, and all result, data, auxiliary-resource,
order, and connection references. Candidate-eligible local IDs are the union of
the selected results' `result_data_links[].data_inputs[].data_id` values. Every
member result must declare the same nonempty set of `input_role:
primary_spatial` IDs, and `spatial_data_ids` must equal that common set exactly.
Record used objects in `used_data_objects[].id` using the Round 3 `data_id`;
this list is `Dxx`-only. Record every used `Axx` separately in
`used_auxiliary_resources[]`.
Compute `chain_id` over `case_id + "\n" +
candidate_id`, with no trailing newline. Persist the manifests'
NAS-data-root-relative paths and consumer-computed raw-byte SHA-256 values in
`chain_manifest.yaml:input_binding`; absolute paths remain dispatch-only values.

## Workflow

For `public_database_stomicsdb`, replace steps 1-3 with manifest binding and
candidate resolution. Derive S00 from referenced data contexts. Construct the
chain only from the selected candidate's ordered results. For each result,
reread only the assigned dataset-local article's declared Results section and
`source_anchors` figure, table, or stable text locators. Use its ordered
analysis steps and resolve inputs through `result_data_links[].data_inputs`,
including `input_role`, exact `sample_ids`, and `required_components`. Reopen
only exact required component paths after verifying that each is a hash-valid
subset of the referenced `Dxx` component files. Do not broaden the candidate,
repeat Round 3 discovery, or infer missing connections. Use
`result_connections` for cross-result continuity. A required `Axx` with
`local_availability: absent` prevents `DATA_READY` but does not prevent
scientific specification extraction when the article and all Dxx inputs are
valid. Preserve its exact case-declared resource name, expected content, source
URL, access classification, and access notes in an external wrapper; do not
invent localization fields. Treat `local_availability: localized` as valid only
when the exact package manifest path, raw-byte hash,
package ID, generation ID, required artifact
paths, and artifact hashes validate against a canonical manifest whose
`auxiliary_localization_manifest.localization_status` is `LOCALIZED`. Require
complete expected-content coverage for the selected requirement. Write the
validated wrapper to `used_auxiliary_resources[]`; its
`canonical_resource_id` and `package_id` both equal the localized package ID.
A URL or downloaded staging artifact is not a local binding.

For every new STOmics draft or revision, write
`chain_manifest.yaml:round3_result_bindings` in candidate `result_order`. Bind
each Rxx to at least one Sxx/Exx pair; cover every non-S00 Sxx and every Exx
exactly once, and keep each Exx linked to an Sxx in the same Rxx binding.

1. Read method-level `screening.yaml` to confirm method/case membership.
2. Do not extract chain artifacts for another `case_id` in the same invocation.
3. Read per-case `case_screen.yaml` as the case-specific context.
4. Read per-case `source_manifest.yaml` for localized source material.
5. Read per-case `case_data_manifest.yaml`. Require
   `case_data_manifest.data_localization_status: DATA_READY` for `tool_method`.
   For `public_database_stomicsdb`, treat Round 3 admission support separately
   from execution availability. Derive readiness from readable, hash-valid
   exact paths in each selected result's `required_components`; any required
   `Axx` with `local_availability: absent` prevents `DATA_READY` but may proceed
   as a `BLOCKED_EXTERNAL` scientific specification under the STOmics candidate
   contract. A localized `Axx` must satisfy the canonical binding and coverage
   checks above.
6. Stop before JSONL extraction if localized source material or required Dxx is
   incomplete. For STOmics only, do not stop when the sole unresolved inputs are
   exact case-declared absent Axx resources.
7. Define one scientific chain scope in `chain_manifest.yaml`.
8. Select `source_analysis_granularity` or `concrete_execution_granularity`.
9. Write `S00` from source screening and localized data summaries for
   `tool_method`; for `public_database_stomicsdb`, derive it only from the bound
   case, source, and data manifests.
   If no selected Axx contributes samples, a non-null `sample_count` must equal
   the selected Dxx sample-ID count. If a canonically localized Axx contributes
   additional samples, a non-null count may cover the full Dxx+Axx scope only
   when the bound manifests support that total, and it must not be smaller than
   the selected Dxx count. Use `null` when the full total is unresolved.
10. Draft HVU candidates from localized source text, figures, tables, notebook outputs, scripts, selected-result files, and localized data summaries.
11. Treat draft candidates as temporary working units. Do not assign Sxx identifiers until candidate checking is complete.
12. Apply the HVU candidate check loop:
    a. identify the scientific target object;
    b. confirm the hypothesis is a neutral analysis target and does not state observed existence, direction, alignment, enrichment, significance, null result, or tool success;
    c. confirm minimum result material, including at least one primary result
       observation;
    d. confirm one result-to-conclusion progression;
    e. confirm contrastive material is split only when it contains independent
       result targets;
    f. place process material in the linked execution subchain,
       `chain_manifest.yaml` context fields, or `observation.support` locators when
       appropriate;
    g. ensure conclusion.summary follows only from the candidate's result observations;
    h. confirm a linked execution route can support the result material.
13. Revise candidates by splitting independent result targets, moving
    process/object-description material to the linked execution subchain,
    `chain_manifest.yaml` context fields, or `observation.support` locators, or
    narrowing conclusions.
14. Repeat the check for affected candidates.
15. Assign final Sxx identifiers only to candidates that pass the loop.
16. For each final HVU, write hypothesis using a neutral analysis-target form such as Evaluate, Compare, Assess, Estimate, or Characterize. Do not use result-direction wording in hypothesis.
17. Draft the linked primary execution subchain.
18. Apply the execution route and subchain check from `docs/datasets/dual-chain-extraction.md`.
19. Revise the HVU/E pair when the route cannot reach result material.
20. Write `result.observations[]` only from result-bearing outputs or source
    result locators aligned with `result_extraction.observations[]`. Result
    observations must include primary result material; descriptive object facts
    may support but not replace it.
21. Write conclusion.summary as a bounded synthesis of the observations, with no added result facts.
22. Continue by final HVU/E alternating expansion.
23. For `tool_method`, start a new chain only when the existing chain-boundary
    rules apply. For `public_database_stomicsdb`, keep the selected candidate in
    one chain directory; if its declared order, references, logical root, or
    required component paths or hashes are contradictory, report the Round 3 handoff as
    `round3_handoff_needs_revision` at the candidate-job boundary instead of
    inventing a scientific repair. Use `needs_revision` only for a correctable
    drafted-chain representation.
24. Record claimed source materials, `Dxx` data objects, and separately bound
    `Axx` auxiliary resources in `chain_manifest.yaml`.
25. Leave object resolution, source-support confirmation, schema checks, and status updates to the chain-independent confirmation stage.

For STOmics, raw/input Dxx and Axx objects establish execution availability
only. They cannot support a new scientific observation unless Round 3
explicitly binds a precomputed result object. Otherwise use the admitted
article anchors. Image-derived content is limited to directly visible labels,
scale bars, counts, regions, and relative distributions; do not infer
unreported significance, causality, mechanism, or biological identity.

Both routes use the unchanged core scientific-chain and execution-subchain JSON
schemas. `source_analysis_granularity` is the minimum acceptable public-data
granularity. Use `concrete_execution_granularity` only when canonical sources
contain source-observed code or workspace detail. Missing code is not a failure
when the source-analysis route is valid.

## Output

When pre-chain localization is complete and route-appropriate readiness is
established (`case_data_manifest.data_localization_status` for `tool_method`,
or derived from exact referenced component paths with no required absent `Axx` for
`public_database_stomicsdb`), and
localized source material supports at least one concrete HVU/E pair, write
exactly these three nonempty chain artifacts directly under the
coordinator-provided extraction-attempt staging directory:

- `chain_manifest.yaml`
- `scientific_chain.jsonl`
- `execution_subchains.jsonl`

Candidate notes are internal working material and are not written as JSONL rows.
JSONL files contain only S00 and final checked HVUs.

Never write the final chain directory. Return the staging path to the
coordinator. The coordinator alone acquires the chain lock, confirms the final
directory is absent, validates the complete three-file cross-reference and
input-hash contract, including every route/identity field, Sxx/E link, Dxx/Axx
wrapper, input manifest hash, JSONL parse/schema result, and nonempty-record
requirement, and atomically renames staging to final on the same NAS filesystem.
An existing final directory requires a separately authorized
replacement transaction with backup; it must never be overwritten by this
curator.

If pre-chain localization is incomplete, stop before writing JSONL files. Report
the required source or data repair target in the working response or a manifest
planning note, not as chain rows.

Scientific rows must contain `hypothesis`, `experiment`, `result`, `conclusion`,
and `next_hypothesis`. Execution rows must contain ordered steps with `inputs`,
`call`, `parameters`, `outputs`, and `source_ref`, plus
`result_extraction.observations[]`. Keep source, provenance, and granularity
metadata in the route-appropriate source/case manifests and
`chain_manifest.yaml`, not in the shared JSONL rows. The public-data chain
manifest binds `case_route`, `stds_id`, `candidate_id`, and path plus SHA-256
for all three case manifests.

Placeholders stay outside JSONL files. `source_ref` points to local source
material. For `concrete_execution_granularity`, inputs, outputs, and calls use
source-observed object names from localized source material.
For `source_analysis_granularity`, use object names and analysis products
denoted by the article or source material, such as named data objects, result
tables, figure panels, reported clusters, gene sets, regions, or reported
analysis outputs.

Set `chain_manifest.yaml` `independent_check.status` to `not_started` by
default. Comparison-ready consideration is handled by the separate
chain-independent confirmation prompt.

If Stage 4 later returns `needs_revision`, any extraction revision is a new
three-file attempt in new staging. The coordinator publishes it under the chain
lock through a recoverable replacement transaction with a complete prior-chain
backup and resets the independent check to `not_started`. Do not edit the
existing JSONL files in place or combine rows from different attempts.

Do not create a formal working-note artifact. Do not store raw datasets, truth
files, trajectories, run outputs, or copied source cache material in this Git
repository.

## Subagent Dispatch

Use `contracts/prompts/curation/dispatch_dual_chain_extraction.md` when
assigning this stage to a subagent. The dispatch prompt points back to this
file as the mandatory stage protocol.

## Visibility

This prompt is curator-only and evaluator-facing. Do not copy it into agent
workspaces, task prompts, run input directories, or agent-visible benchmark
materials.

# Dual-Chain Chain-Independent Confirmation

## Purpose

Use this internal prompt to confirm drafted case-derived dual-chain artifacts
after extraction. The workflow checks whether the chain record is concrete,
source/data-traceable, and process-ready for comparison-ready consideration.

## Inputs

Set `case_route: tool_method | public_database_stomicsdb`.

For `tool_method`, use the existing inputs below:

- `method_screening_yaml`:
  `raw_data/tool_method/<method_slug>/screen/screening.yaml`.
- `method_slug`.
- `case_id`.
- Per-case `case_screen.yaml` from
  `raw_data/tool_method/<method_slug>/cases/<case_id>/case_screen.yaml`.
- Per-case `source_manifest.yaml` from
  `raw_data/tool_method/<method_slug>/cases/<case_id>/source_manifest.yaml`
  for localized source material and acquisition scope.
- Per-case `case_data_manifest.yaml` from
  `raw_data/tool_method/<method_slug>/cases/<case_id>/data/case_data_manifest.yaml`
  for localized data records and data readiness.
- Localized source materials from the package-local `source/` and case source
  records, such as source documents, source pages, tutorials, examples,
  vignettes, notebooks, scripts, code snapshots, and download logs when
  permitted.
- Chain directory:
  `raw_data/tool_method/<method_slug>/cases/<case_id>/dual_chain/<chain_id>/`.
- Unique absolute NAS review-attempt staging directory.
- Draft `chain_manifest.yaml`, `scientific_chain.jsonl`, and
  `execution_subchains.jsonl`.

One invocation confirms one existing `dual_chain/<chain_id>/` directory for the
specified `case_id`.

For `public_database_stomicsdb`, use instead `stds_id`, one `candidate_id`,
absolute paths to canonical `case_manifest.yaml`, `source_manifest.yaml`, and
`data/case_data_manifest.yaml`, the deterministic `chain_id`, the final
public-case chain directory, the extraction-attempt staging path bound by the
queue row, and a unique absolute NAS review-attempt staging directory. Derive
`case_id` as `stomicsdb_<STDS_ID>`. Do not require `method_slug`,
`screening.yaml`, or `case_screen.yaml`. Consume the coordinator-validated
immutable three-manifest and Dxx/Axx bindings; do not independently rehash
large data artifacts. Verify the chain's binding identities and resolve its
persisted local paths as NAS-data-root-relative values.

## Workflow

For `public_database_stomicsdb`, replace steps 1-3 with verification of the
three-manifest binding and selected candidate. Apply the ten lightweight checks
below without repeating Round 3 discovery:

1. The three manifests parse and have the assigned `stds_id`.
2. The selected `candidate_id` exists.
3. Every `result_id`, `Dxx`, and `Axx` reference resolves, and every
   `used_data_objects[].id` equals a Round 3 `data_id` in the candidate results'
   `result_data_links[].data_inputs`. Every member result declares the same
   nonempty `primary_spatial` set, and candidate `spatial_data_ids` equals that
   set exactly. `used_data_objects[]` contains no `Axx`; each used `Axx`
   resolves separately through `used_auxiliary_resources[]`.
4. `result_order` contains exactly the candidate result set without duplicates.
5. Every connection references candidate results and its `from_output` and
   `to_input` values match the corresponding analysis steps.
6. Every connected result uses the same primary logical spatial `Dxx` and its
   declared connection matches that route.
7. S00 uses only referenced data contexts.
8. Each HVU/E pair is supported by the selected result's `source_anchors`
   figure, table, or stable text locators and analysis steps.
9. Each required component path is a readable, hash-valid subset of the
   referenced `Dxx` component files and agrees with declared sample IDs.
10. External `Axx` inputs retain their actual limitation. Any required `Axx`
    with `local_availability: absent` prevents `DATA_READY`, but its
    specification may be confirmed when the wrapper exactly preserves the
    Round 3 identity and no localization content is invented. A localized
    `Axx` is valid only when its canonical package ID, exact package
    manifest path and raw-byte hash, package and generation IDs, required
    artifact paths and hashes, and complete expected-content coverage validate
    against a canonical manifest whose
    `auxiliary_localization_manifest.localization_status` is `LOCALIZED`. The
    wrapper's `canonical_resource_id` and `package_id` both equal that
    localized package ID.
11. `round3_result_bindings` follows candidate `result_order` exactly and maps
    every non-S00 Sxx and Exx to one and only one member result.

1. Read method-level `screening.yaml` to confirm method/case membership.
2. Do not update confirmation fields for other chains in the same invocation.
3. Read per-case `case_screen.yaml` as the case-specific context.
4. Read per-case `source_manifest.yaml` and localized source material.
5. Read per-case `case_data_manifest.yaml`. Before setting
   `independent_check.status: confirmed`, require
   `case_data_manifest.data_localization_status: DATA_READY` for `tool_method`;
   for `public_database_stomicsdb`, distinguish Round 3 admission support from
   execution availability. Derive readiness from exact readable, hash-valid
   required component paths. Permit an absent `Axx` only for
   `specification_ready`, verify its exact case-declared external wrapper, and
   validate every localized `Axx` against its canonical `LOCALIZED` manifest
   and complete expected-content coverage.
6. Read `chain_manifest.yaml`, `scientific_chain.jsonl`, and
   `execution_subchains.jsonl`.
7. Parse every non-empty JSONL line and validate each record against:
   - `contracts/schemas/scientific_chain.schema.json`;
   - `contracts/schemas/execution_subchains.schema.json`.
   Record a parse or schema failure as `needs_revision`. A schema failure is not
   `blocked` when the underlying source and localized data remain available.
8. Write exactly two nonempty files, a proposed full `chain_manifest.yaml` and
   `independent_check.md`, in the coordinator-provided review staging
   directory.
9. In the proposal, record summary findings, `notes_location`, and final
   independent-check status in `chain_manifest.yaml:independent_check`.
10. Keep proposed `chain_manifest.yaml:chain_status` consistent with the
    confirmation outcome.
11. Leave `scientific_chain.jsonl` and `execution_subchains.jsonl` unchanged.
    Correctable extraction issues are recorded as revision findings.
12. Never write the final chain directory. Return the review staging path and
    the raw-byte hashes of the final manifest and both JSONL files inspected.

This stage confirms procedural chain quality: structure, granularity,
source/data traceability, and HVU/E alignment. It does not decide whether the
publication conclusion is scientifically true.

## Stage 4 Review Rules

### Status Decision Workflow

Apply these decisions in order:

1. Report `blocked` to the candidate controller only when confirmation cannot
   proceed because:
   - for `tool_method`, method/case membership cannot be established;
   - for `public_database_stomicsdb`, the three-manifest binding or
     selected-candidate membership cannot be checked because a bound input is absent,
     unreadable, or does not match its recorded hash;
   - the physical route-appropriate readiness condition is not satisfied; for
     STOmics, an exact absent-Axx wrapper alone is not a physical blocker;
   - a required localized input data object does not exist, cannot be read, or is the wrong sample/object;
   - source evidence required to support the primary result observation is absent or unreadable.
   Do not publish a blocked STOmics chain manifest; the controller closes the
   job from the physical input failure.
2. For `public_database_stomicsdb`, set `needs_revision` with
   `revision_scope: round3_handoff` against the Round 3
   handoff when the bound inputs are available and hash-valid but their declared
   source, data, or route structure cannot support any schema-valid HVU/E pair.
   The candidate-job controller maps this unresolved handoff finding to terminal
   `round3_handoff_needs_revision`; that value is not written as a
   `chain_status`.
3. Set `needs_revision` with `revision_scope: extraction` when required source
   and input data are available, but the drafted chain has correctable
   representation problems, including HVU granularity, hypothesis wording,
   result placement, source locator expression, execution detail, object
   continuity, data-object references, or conclusion closure.
4. Set `confirmed` only when no blocking or revision item remains.
5. Use `not_started` only before Stage 4 review begins.

### Case-Derived Execution Confirmation

For a case-derived chain, confirm the execution route from localized source
material. Do not execute, replay, or rerun the method during Stage 4. An
official tutorial or example remains a valid case source when it provides a
specific data context and a source-observed workflow.

For `concrete_execution_granularity`, confirm source-observed input objects,
function or method calls, key parameters, and output transitions. A
source-observed assignment, return value, object mutation, export target, or
saved path may serve as an execution output even when it was not regenerated
locally.

For `source_analysis_granularity`, confirm source-denoted analysis inputs,
methods, result objects, and source locators.

Missing packages, environments, model replay, or regenerated outputs are not
Stage 4 findings by themselves. This rule does not waive the requirement that
the case's declared input data objects exist and match the registered case
scope. Scientific result content still requires source-retained result evidence;
a declared output object alone is execution evidence, not a primary scientific
observation.

For public data, absent source-observed code is not a failure when the route is
valid at `source_analysis_granularity`. Null or non-significant source results
are valid primary result material. A declared structural omission in an
otherwise available, hash-valid Round 3 handoff is `needs_revision`, not an
instruction to invent content. An absent or unreadable article, Dxx, or claimed
localized Axx remains `blocked`. A case-declared absent Axx instead remains an
explicit `BLOCKED_EXTERNAL` limitation of a `specification_ready` chain.
At job closure, an unresolved handoff-level finding maps to
`round3_handoff_needs_revision`; ordinary correctable extraction findings stay
in the bounded repair loop.

### Result Evidence Review Order

Review each primary scientific observation in this order:

1. Read source result statements, figure or table captions, legends, titles,
   axis labels, and table entries.
2. Read retained notebook text, structured outputs, and source-reported result
   values.
3. Inspect a source-retained figure or notebook image only when the preceding
   material does not fully specify the bounded observation.

Do not request additional result material when the earlier evidence already
supports the observation. Missing optional figures, rendered pages, result
archives, or generated directories are not findings by themselves.

An image-derived observation must remain directly visible and bounded. It may
describe a labeled count, value, layer, contiguous region, localized focus,
relative distribution, or explicit absence. It must not add a biological label,
statistical significance, ground-truth agreement, causal interpretation, or
mechanism that is not supplied by the source text or figure annotations.

Raw/input Dxx and Axx objects prove execution availability only. They do not
support a new scientific observation unless Round 3 explicitly binds a
precomputed result object.

- Every non-`S00` HVU must have one scientific or result object. The reviewer
  checks each `result.observations[]` entry against that same HVU target.
- A hypothesis must be written as a testable or question-like target. It must
  not pre-write the positive, negative, or null result direction that belongs in
  `result` and `conclusion`.
- If any non-S00 HVU hypothesis states observed direction, existence,
  alignment, enrichment, significance, null result, or tool success, set
  independent_check.status to needs_revision unless a higher-severity blocked
  issue applies.
- A null or non-significant result can be primary result material, but the
  hypothesis must not be rewritten as a positive-result claim.
- Object existence, table shape, column names, file availability, model object
  content, and plotting availability are support or context only, unless the
  source itself reports them as the result target.
- Execution chain details at notebook-cell, function-call, object-name,
  parameter, and saved-output granularity are positive evidence when they are
  source-backed and linked to the HVU. If the manifest granularity label
  disagrees with the execution rows, record a manifest metadata revision.
- Use the `docs/datasets/data-contract.md` Chain Data Object References rules
  when checking `used_data_objects`. This field is `Dxx`-only. Validate each
  `Axx` through `used_auxiliary_resources[]` and its canonical localization
  binding. Bare internal artifact names require a
  reference-expression revision, not a scientific-chain failure by themselves.
- `used_localized_sources` may contain data-root-relative source paths as shown
  in the chain-manifest template. Confirm that each claimed path resolves and is
  consistent with localized source records. Do not require source IDs, roles, or
  locator mappings in this field.
- Keep `findings_summary.blocking`, `needs_revision`, and `notes` as lists of
  scalar strings. Quote YAML strings containing `:` so they are not parsed as
  mappings.
- A missing or imprecise `used_data_objects` artifact reference is
  `needs_revision` when the underlying registered data object is available. It
  becomes `blocked` only when the required data object itself is unavailable,
  unreadable, or the wrong object.

## `independent_check.md` Template

```markdown
# Independent Check: <case_route> / <case_id> / <chain_id>

## Summary

- Overall result:
- Chain status recommendation:
- Main revision items:
- Main notes:

## Checklist

### 1. Case Membership

- Evidence inspected:
- Finding:
- Action for this chain:

### 2. Data Readiness

- Evidence inspected:
- Finding:
- Action for this chain:

### 3. Source Traceability

- Evidence inspected:
- Finding:
- Action for this chain:

### 4. Scientific Chain Structure

- Evidence inspected:
- Scientific JSONL parse/schema result:
- Hypothesis-result-conclusion polarity checked:
- Hypothesis form verdicts:
  - Sxx: confirmed | needs_revision; reason:
- Null/negative-result hypothesis expression checked:
- Finding:
- Action for this chain:

### 5. HVU Granularity

- Evidence inspected:
- Same scientific/result object per observation checked:
- Split direction if target, evidence type, or result-to-conclusion progression differs:
- Finding:
- Action for this chain:

### 6. Primary Result Material

- Evidence inspected:
- Primary result pattern/value/marker/region/statistic/null result checked:
- Support/context object placement checked:
- Finding:
- Action for this chain:

### 7. Execution Chain Structure

- Evidence inspected:
- Execution JSONL parse/schema result:
- Concrete execution detail linked to HVU checked:
- Input -> call(parameters) -> output continuity checked:
- Finding:
- Action for this chain:

### 8. Execution-To-Result Alignment

- Evidence inspected:
- Execution bridge to result observation checked:
- Finding:
- Action for this chain:

### 9. Data Object Consistency

- Evidence inspected:
- Chain Data Object References rule checked:
- Finding:
- Action for this chain:

### 10. Conclusion Placement

- Evidence inspected:
- Finding:
- Action for this chain:

## Findings Summary

- Blocking:
- Needs revision:
- Notes:
```

Use concrete findings. Keep items short. Record actual nonconformities and
relevant notes. Do not use this review to decide whether the publication
conclusion is scientifically true.

## Output

Write exactly two nonempty files, a proposed `independent_check.md` and a
proposed full `chain_manifest.yaml`, in the unique review-attempt staging
directory. Record
the summary result in the proposed
`chain_manifest.yaml:independent_check` using this structure:

```yaml
independent_check:
  status: not_started | confirmed | needs_revision | blocked
  reviewer_independence: independent_curator
  revision_scope: null | extraction | round3_handoff
  checked_sources:
    - source_id:
      local_path:
      source_role:
      locator:
  checked_data_objects:
    - id:
      role:
      local_or_prepared_path:
      artifact_refs:
        - name:
          role:
          path_or_locator:
      read_summary_used:
  checked_unresolved_auxiliary_resource_ids:
    - A01
  findings_summary:
    blocking:
      - "<blocking finding>"
    needs_revision:
      - "<revision finding>"
    notes:
      - "<note>"
  notes_location: dual_chain/<chain_id>/independent_check.md
```

Status semantics:

- `confirmed`: extracted chain records are concrete and source/data-traceable.
  They are process-ready for `comparison_ready` when backed by
  `case_data_manifest.yaml:case_data_manifest.data_localization_status:
  DATA_READY` for `tool_method`, or by derived readiness from readable eligible
  logical `Dxx` roots, every exact hash-valid required component path, and no
  required `Axx` with `local_availability: absent` for
  `public_database_stomicsdb`. When only exact absent-Axx wrappers remain,
  confirmation instead recommends `specification_ready` and retains
  `BLOCKED_EXTERNAL`. `confirmed` is invalid unless required local Dxx and
  localized Axx objects resolve and cite local paths. External Axx wrappers are
  checked against Round 3 identity fields, never against invented local paths.
- `needs_revision`: chain remains draft material with a machine-readable
  extraction or Round 3 handoff scope.
- `blocked`: required source material or localized data needed for confirmation
  is unavailable.

`chain_manifest.yaml:independent_check.findings_summary` is a concise summary
of the Markdown review. Put detailed checklist findings in
`independent_check.md`.

For STOmics, `checked_data_objects[].id` equals the exact union of selected Dxx
and localized Axx IDs, and every path is NAS-data-root-relative and readable.
`checked_unresolved_auxiliary_resource_ids` equals the selected absent Axx IDs.
Every member Rxx has a recorded checked source locator. A confirmed STOmics
review is invalid for `self_review_with_limitation`.

Set `chain_manifest.yaml:chain_status` from the final independent-check status:

- `not_started` -> `draft`
- `confirmed` -> `comparison_ready` when `DATA_READY`, otherwise
  `specification_ready` when only exact absent-Axx dependencies remain
- `needs_revision` -> `needs_revision`
- `blocked` -> `blocked`

Do not write any other `chain_status` value.

The independent reviewer never edits final files. After the reviewer returns,
the coordinator acquires the chain lock and, under that lock, reopens all final
and proposed files and verifies that the final scientific and execution JSONL
raw-byte hashes are unchanged, that the proposed full manifest differs from the
current manifest only in Stage 4-owned fields, and that the proposed status
matches `independent_check.md`. Without releasing the lock, publish through a
recoverable per-chain replacement transaction: record `PREPARED`, back up the
current final manifest and review file when present, install the proposed
files, verify the final tree and unchanged JSONL hashes, then record
`COMMITTED`. On any post-prepare failure restore and verify the backup and
record `ROLLED_BACK`. Keep the transaction and backup as durable NAS evidence.

A `needs_revision` review records findings only. Any revised extraction is a
new three-file Stage 3 product in new staging and is published by the
coordinator through a separate locked replacement transaction with a complete
prior-chain backup. The replacement resets
`independent_check.status: not_started`. Never edit or regenerate JSONL during
review and never merge rows from old and new extraction attempts.

## Subagent Dispatch

Use `contracts/prompts/curation/dispatch_dual_chain_independent_check.md` when
assigning this stage to a subagent. The dispatch prompt points back to this
file as the mandatory stage protocol.

## Visibility

This prompt and its confirmation output are curator/evaluator-facing. Store
retained notes in internal NAS curation material, not in Git and not in agent
workspaces, task prompts, run input directories, or benchmark-visible material.

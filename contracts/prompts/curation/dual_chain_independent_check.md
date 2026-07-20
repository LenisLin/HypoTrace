# Dual-Chain Chain-Independent Confirmation

## Purpose

Use this internal prompt to confirm drafted case-derived dual-chain artifacts
after extraction. The workflow checks whether the chain record is concrete,
source/data-traceable, and process-ready for comparison-ready consideration.

## Inputs

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
- Draft `chain_manifest.yaml`, `scientific_chain.jsonl`, and
  `execution_subchains.jsonl`.

One invocation confirms one existing `dual_chain/<chain_id>/` directory for the
specified `case_id`.

## Workflow

1. Read method-level `screening.yaml` to confirm method/case membership.
2. Do not update confirmation fields for other chains in the same invocation.
3. Read per-case `case_screen.yaml` as the case-specific context.
4. Read per-case `source_manifest.yaml` and localized source material.
5. Read per-case `case_data_manifest.yaml` and verify
   `case_data_manifest.data_localization_status: DATA_READY` before setting
   `independent_check.status: confirmed`.
6. Read `chain_manifest.yaml`, `scientific_chain.jsonl`, and
   `execution_subchains.jsonl`.
7. Parse every non-empty JSONL line and validate each record against:
   - `contracts/schemas/scientific_chain.schema.json`;
   - `contracts/schemas/execution_subchains.schema.json`.
   Record a parse or schema failure as `needs_revision`. A schema failure is not
   `blocked` when the underlying source and localized data remain available.
8. Write `independent_check.md` using the checklist template below.
9. Record summary findings, `notes_location`, and final independent-check status
   in `chain_manifest.yaml:independent_check`.
10. Keep `chain_manifest.yaml:chain_status` consistent with the confirmation
   outcome.
11. Leave `scientific_chain.jsonl` and `execution_subchains.jsonl` unchanged.
    Correctable extraction issues are recorded as revision findings.

This stage confirms procedural chain quality: structure, granularity,
source/data traceability, and HVU/E alignment. It does not decide whether the
publication conclusion is scientifically true.

## Stage 4 Review Rules

### Status Decision Workflow

Apply these decisions in order:

1. Set `blocked` only when confirmation cannot proceed because:
   - method/case membership cannot be established;
   - `case_data_manifest.yaml` is not `DATA_READY`;
   - a required localized input data object does not exist, cannot be read, or is the wrong sample/object;
   - source evidence required to support the primary result observation is absent or unreadable.
2. Set `needs_revision` when required source and input data are available, but the drafted chain has correctable representation problems, including HVU granularity, hypothesis wording, result placement, source locator expression, execution detail, object continuity, data-object references, or conclusion closure.
3. Set `confirmed` only when no blocking or revision item remains.
4. Use `not_started` only before Stage 4 review begins.

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
  when checking `used_data_objects`. Bare internal artifact names require a
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
# Independent Check: <method_slug> / <case_id> / <chain_id>

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

Write `independent_check.md` in the chain directory. Record the summary result in
`chain_manifest.yaml:independent_check` using this structure:

```yaml
independent_check:
  status: not_started | confirmed | needs_revision | blocked
  reviewer_independence: independent_curator | self_review_with_limitation
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

- `confirmed`: extracted chain records are concrete, source/data-traceable,
  process-ready for comparison-ready consideration, and backed by
  `case_data_manifest.yaml:case_data_manifest.data_localization_status:
  DATA_READY`. `confirmed` is invalid unless required data objects resolve and
  checked data objects cite local or prepared paths.
- `needs_revision`: chain remains draft material with correctable extraction
  issues.
- `blocked`: required source material or localized data needed for confirmation
  is unavailable.

`chain_manifest.yaml:independent_check.findings_summary` is a concise summary
of the Markdown review. Put detailed checklist findings in
`independent_check.md`.

Set `chain_manifest.yaml:chain_status` from the final independent-check status:

- `not_started` -> `draft`
- `confirmed` -> `comparison_ready`
- `needs_revision` -> `needs_revision`
- `blocked` -> `blocked`

Do not write any other `chain_status` value.

## Subagent Dispatch

Use `contracts/prompts/curation/dispatch_dual_chain_independent_check.md` when
assigning this stage to a subagent. The dispatch prompt points back to this
file as the mandatory stage protocol.

## Visibility

This prompt and its confirmation output are curator/evaluator-facing. Store
retained notes in internal NAS curation material, not in Git and not in agent
workspaces, task prompts, run input directories, or benchmark-visible material.

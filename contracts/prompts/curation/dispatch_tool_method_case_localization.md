# Dispatch: Tool/Method Case Localization

This is a subagent entry for assigning one localization task. It is not the
stage protocol.

Stage: tool/method case localization.

## Required Inputs

- `method_screening_yaml`
- `method_slug`
- `case_id`
- NAS data root

## Required References

Read these project documents before acting:

- `docs/datasets/tool-method-case-extraction.md`
- `docs/datasets/data-contract.md`
- `docs/datasets/dual-chain-extraction.md`

## Required Templates

Use these canonical templates and semantics:

- `docs/datasets/tool-method-case-extraction.md` source localization YAML
  template.
- `docs/datasets/tool-method-case-extraction.md` case data localization YAML
  template.
- `docs/datasets/data-contract.md` NAS layout, active localization loop, final
  status values, route-completion semantics, manifest write hygiene,
  Case-reference reuse semantics, and `DATA_READY` semantics.

## Mandatory Stage Protocol

Follow `contracts/prompts/curation/tool_method_case_localization.md`.

## Output Paths

- `raw_data/tool_method/<method_slug>/cases/<case_id>/case_screen.yaml`
- `raw_data/tool_method/<method_slug>/cases/<case_id>/source_manifest.yaml`
- `raw_data/tool_method/<method_slug>/cases/<case_id>/data/case_data_manifest.yaml`
- `raw_data/tool_method/<method_slug>/cases/<case_id>/data/objects/<data_object_id>/`
- `raw_data/tool_method/<method_slug>/cases/<case_id>/data/samples/<sample_id>/`

## Boundary

Write localization outputs only. Do not write `chain_manifest.yaml`,
`scientific_chain.jsonl`, `execution_subchains.jsonl`, or independent-check
artifacts.

The subagent runs the active localization loop until `DATA_READY` or
`BLOCKED_EXTERNAL`; route probing alone is not completion, and
`DATA_REPAIR_REQUIRED` is internal and not a final output. The subagent ends
only after `DATA_READY` or `BLOCKED_EXTERNAL` is recorded in YAML-parseable
manifests.
For article-derived cases, the subagent records original paper PDF/text plus
the exact case-bearing source material before ending localization. For official
tutorial cases, it records the exact tutorial, notebook, script, or example
source material. The stage protocol in `tool_method_case_localization.md`
remains the source of truth.
It also ends only after YAML parse confirms controlled final status/visibility
values: `case_data_manifest.data_localization_status` is `DATA_READY` or
`BLOCKED_EXTERNAL`, and `case_data_manifest.data_objects[].visibility` uses
only `agent_input_candidate`, `evaluator_context_only`, or
`excluded_derived_output`.

The subagent may reference existing artifacts from another case when
Case-reference reuse applies, but current-case manifests remain required and it
writes localization manifests only for the specified `case_id`.

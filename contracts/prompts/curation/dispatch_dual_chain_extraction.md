# Dispatch: Dual-Chain Extraction

This is a subagent entry for assigning one dual-chain extraction task. It is
not the stage protocol.

Stage: dual-chain extraction.

## Required Inputs

- `method_screening_yaml`
- `method_slug`
- `case_id`
- Per-case `case_screen.yaml`
- Per-case `source_manifest.yaml`
- Per-case `case_data_manifest.yaml` with
  `case_data_manifest.data_localization_status: DATA_READY`
- Target chain directory for one `chain_id` under
  `raw_data/tool_method/<method_slug>/cases/<case_id>/dual_chain/<chain_id>/`

## Required References

Read these project documents before acting:

- `docs/datasets/tool-method-case-extraction.md`
- `docs/datasets/data-contract.md`
- `docs/datasets/dual-chain-extraction.md`

## Required Templates

Use these canonical templates:

- `docs/datasets/dual-chain-extraction.md` `chain_manifest.yaml` Template.
- `contracts/output_template/scientific_chain.jsonl`
- `contracts/output_template/execution_subchains.jsonl`

## Mandatory Stage Protocol

Follow `contracts/prompts/curation/dual_chain_extraction.md`.

## Output Paths

Write the chain artifacts under the target chain directory:

- `chain_manifest.yaml`
- `scientific_chain.jsonl`
- `execution_subchains.jsonl`

## Boundary

Write chain extraction outputs only. Independent confirmation is a later stage.
Do not alter localization outputs except to report blockers.

The subagent must follow the HVU candidate check loop and the execution route and subchain check in `contracts/prompts/curation/dual_chain_extraction.md` before writing final `scientific_chain.jsonl` and `execution_subchains.jsonl`.

The subagent handles only the specified `case_id` and target chain directory.
Additional chain scopes are reported for separate dispatch.

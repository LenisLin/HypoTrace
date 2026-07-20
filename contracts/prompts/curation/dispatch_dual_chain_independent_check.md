# Dispatch: Dual-Chain Independent Check

This is a subagent entry for assigning one independent-check task. It is not
the stage protocol.

Stage: dual-chain independent confirmation.

## Required Inputs

- `method_screening_yaml`
- `method_slug`
- `case_id`
- Per-case `case_screen.yaml`, `source_manifest.yaml`, and
  `case_data_manifest.yaml`
- Chain directory for one `chain_id` under
  `raw_data/tool_method/<method_slug>/cases/<case_id>/dual_chain/<chain_id>/`

## Required References

Read these project documents before acting:

- `docs/datasets/tool-method-case-extraction.md`
- `docs/datasets/data-contract.md`
- `docs/datasets/dual-chain-extraction.md`

Use `docs/datasets/data-contract.md` Chain Data Object References when checking
`chain_manifest.yaml:used_data_objects`.

## Required Templates

Use these canonical templates:

- `docs/datasets/dual-chain-extraction.md` `chain_manifest.yaml` Template.
- `contracts/output_template/scientific_chain.jsonl`
- `contracts/output_template/execution_subchains.jsonl`

## Mandatory Stage Protocol

Follow `contracts/prompts/curation/dual_chain_independent_check.md`.

## Output Path

- In the specified chain directory, write `independent_check.md`.
- Update that directory's `chain_manifest.yaml:independent_check`, compatible
  `chain_status`, and `notes_location`.

## Boundary

Write the review file and manifest summary only. Do not write screening outputs,
localization outputs, new chain extraction artifacts, or edited JSONL chain artifacts.

Confirm case-derived execution from localized source material for both declared
granularities. Do not execute, replay, or regenerate the method. Check
source-observed `input -> call(parameters) -> output` continuity and preserve
real missing or mismatched required input objects as blockers.

Apply the Result Evidence Review Order from the mandatory Stage 4 protocol.
Judge source localization for support of the written observation, not for
complete collection of every available figure, rendered page, or generated
artifact.

Apply the neutral-hypothesis rule to every non-S00 HVU. A directional
hypothesis is a correctable extraction issue and should be recorded as
needs_revision.

Record correctable extraction and reference-expression issues only in
`independent_check.md` and `chain_manifest.yaml:independent_check`; do not
modify JSONL chain artifacts during this stage.

The subagent handles only the specified `case_id` and chain directory. It
updates only that chain's `independent_check.md` and `chain_manifest.yaml`.

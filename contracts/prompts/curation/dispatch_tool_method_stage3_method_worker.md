# Dispatch: Tool/Method Stage 3 Method Worker

This is an orchestration wrapper for running dual-chain extraction for one
method after human-in-loop case review. It is not a new stage protocol.

## Required Inputs

- `batch_id`
- `method_slug`
- Method-level screening path:
  `raw_data/tool_method/<method_slug>/screen/screening.yaml`
- Human-reviewed Stage 3 queue rows for this method.
- NAS data root: `/mnt/NAS_21T/ProjectData/HypoTrace_Data`.

Each queue row should include `case_id`, `chain_id`, human decision, and an
optional human note.

## Required References

Read these project documents and prompts before acting:

- `docs/datasets/tool-method-case-extraction.md`
- `docs/datasets/data-contract.md`
- `docs/datasets/dual-chain-extraction.md`
- `contracts/prompts/curation/dual_chain_extraction.md`
- `contracts/prompts/curation/dispatch_dual_chain_extraction.md`

## Mandatory Protocol

Use `dual_chain_extraction.md` and `dispatch_dual_chain_extraction.md` for each
approved `case_id` and `chain_id`. This wrapper only provides method-level
orchestration over the human-reviewed queue.

## Boundary

Process only queue rows with a human decision to enter Stage 3. Do not add new
cases, process excluded or deferred cases, process `BLOCKED_EXTERNAL` cases,
merge multiple cases into one chain, or write independent-check artifacts.

## Required Response

Report queue cases processed, chains written, no-chain cases with reasons,
blocked cases caused by missing Stage 2 readiness, parse status for written
files, and HVU/execution-subchain counts per chain.

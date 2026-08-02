# Dispatch: Tool/Method Stage 1-2 Method Worker

This is an orchestration wrapper for one method seed. It is not a new stage
protocol.

## Stage Scope

- Stage 1: method-level tool/method case screening.
- Stage 2: case-level source/data localization for every screened `case_id`.

## Required Inputs

- `batch_id`
- `method_slug`
- `method_name`
- Registry seed fields when available: title, DOI, PMID, venue, year,
  GitHub URL, analysis problem, subtask, method family, main input, and main
  output.
- NAS data root: `/mnt/NAS_21T/ProjectData/HypoTrace_Data`.

## Required References

Read these project documents and prompts before acting:

- `docs/datasets/tool-method-case-extraction.md`
- `docs/datasets/data-contract.md`
- `contracts/prompts/curation/tool_method_case_screening.md`
- `contracts/prompts/curation/tool_method_case_localization.md`
- `contracts/prompts/curation/dispatch_tool_method_case_localization.md`

## Mandatory Protocols

Use `tool_method_case_screening.md` for Stage 1 and
`tool_method_case_localization.md` for every Stage 2 case. This wrapper only
orchestrates their order and coverage.

## Output Paths

Write outputs under:

- `raw_data/tool_method/<method_slug>/screen/`
- `raw_data/tool_method/<method_slug>/source/`
- `raw_data/tool_method/<method_slug>/cases/<case_id>/`

## Boundary

Do not write dual-chain artifacts or independent-check artifacts. Do not skip
screened cases because of priority, expected yield, or convenience. Do not
write shared batch Markdown files from concurrent method workers.

## Required Response

Report screening status, total `cases[]`, one row per case with final Stage 2
status, key localized objects, blockers if any, and whether every screened
case reached `DATA_READY` or `BLOCKED_EXTERNAL`.

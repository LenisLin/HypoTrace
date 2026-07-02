# GBM Hypoxia-TAM Reference Demo

This directory is a public, complete demonstration of publication-derived reference extraction for HypoTrace.
It intentionally includes both agent-facing material and gold/reference material so reviewers can inspect the end-to-end output shape.

## Status

- Demo type: public full-gold demonstration.
- Benchmark status: not a hidden evaluation task.
- Paper: Identification of hypoxic macrophages in glioblastoma with therapeutic potential for vasculature normalization.
- Paper/data locator: paper title: Identification of hypoxic macrophages in glioblastoma with therapeutic potential for vasculature normalization; public accessions: NGDC PRJCA008116 / OMIX002713, GEO GSE194329, OMIX003593.
- Data bundle status: not packaged as a runnable HypoTrace NAS task bundle.

## Files

| File | Role |
| --- | --- |
| `task_prompt.md` | Agent-facing task prompt preview. |
| `data_manifest.yaml` | Agent-facing data manifest preview with NAS-style locator placeholders. |
| `starter_workspace_README.md` | Starter workspace notes for the agent-visible side. |
| `analysis_logic_chain.jsonl` | Full machine-readable analysis logic chain extracted from the paper. |
| `analysis_logic_chain.md` | Human-readable review of the analysis logic chain. |
| `reference_scientific_chain.json` | HypoTrace reference scientific-chain draft exported from the logic chain. |
| `reference_claim_surface.json` | HypoTrace reference claim-surface draft. |
| `reference_execution_chain.json` | HypoTrace reference execution-chain draft. |
| `curation_notes.md` | Curation notes, boundary decisions, and promotion checklist. |
| `review_notes.md` | Public-demo review boundary and file guide. |

## Visibility Boundary

This demo exposes gold/reference material for review and demonstration.
It should not be used as a hidden benchmark case.

For real HypoTrace benchmark tasks, keep these materials outside the public task registry and outside the agent workspace:

- reference chains and claim surfaces
- curation notes
- grading rubrics and evaluator prompts
- truth files and reference outputs
- raw or prepared datasets that belong in the NAS bundle

A production benchmark should use the lightweight Git registry shape under `tasks/<task_id>/` and store hidden material under the NAS/evaluator-only bundle.

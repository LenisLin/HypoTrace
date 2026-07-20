# Dual-Chain Extraction Curator Prompt

## Purpose

Use this internal prompt to construct case-derived dual-chain artifacts from a
screened source case. The output is evaluator-facing curation material, not an
agent-facing task prompt and not a ground-truth trajectory.

## Inputs

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
- Target chain directory:
  `raw_data/tool_method/<method_slug>/cases/<case_id>/dual_chain/<chain_id>/`.

One invocation handles one specified `case_id` and one target
`dual_chain/<chain_id>/` directory.

## Workflow

1. Read method-level `screening.yaml` to confirm method/case membership.
2. Do not extract chain artifacts for another `case_id` in the same invocation.
3. Read per-case `case_screen.yaml` as the case-specific context.
4. Read per-case `source_manifest.yaml` for localized source material.
5. Read per-case `case_data_manifest.yaml` and require
   `case_data_manifest.data_localization_status: DATA_READY`.
6. Stop before JSONL extraction if localized source material or case data readiness is incomplete.
7. Define one scientific chain scope in `chain_manifest.yaml`.
8. Select `source_analysis_granularity` or `concrete_execution_granularity`.
9. Write `S00` from source screening and localized data summaries.
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
23. Start a new chain only when chain-boundary rules apply.
24. Record claimed source materials and data objects in `chain_manifest.yaml`.
25. Leave object resolution, source-support confirmation, schema checks, and status updates to the chain-independent confirmation stage.

## Output

When pre-chain localization is complete,
`case_data_manifest.yaml:case_data_manifest.data_localization_status` is
`DATA_READY`, and
localized source material supports at least one concrete HVU/E pair, write the
chain artifacts under the target `dual_chain/<chain_id>/` directory:

- `chain_manifest.yaml`
- `scientific_chain.jsonl`
- `execution_subchains.jsonl`

Candidate notes are internal working material and are not written as JSONL rows.
JSONL files contain only S00 and final checked HVUs.

If pre-chain localization is incomplete, stop before writing JSONL files. Report
the required source or data repair target in the working response or a manifest
planning note, not as chain rows.

Scientific rows must contain `hypothesis`, `experiment`, `result`, `conclusion`, and `next_hypothesis`. Execution rows must contain ordered steps with `inputs`, `call`, `parameters`, `outputs`, and `source_ref`, plus `result_extraction.observations[]`. Keep source, provenance, and granularity metadata in
method-level `screening.yaml`, per-case `case_screen.yaml`,
`source_manifest.yaml`, and `chain_manifest.yaml`, not in the shared JSONL rows.

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

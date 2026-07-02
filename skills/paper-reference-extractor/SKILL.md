---
name: paper-reference-extractor
description: Extract publication-derived reference analysis logic chains from spatial transcriptomics, single-cell, or omics analysis papers. Use when building HypoTrace evaluator-only reference anchors, paper-derived benchmark cases, evidence-grounded analysis logic chain JSONL, or human-readable curation notes from papers and public data availability statements.
---

# Paper Reference Extractor

Use this skill to turn a reproducible omics or spatial-transcriptomics analysis paper into a publication-derived reference chain for HypoTrace curation.

The output is a structured reference anchor, not a paper summary, not the author's private reasoning, and not a unique ground-truth workflow. For public demos, gold/reference files may be shown explicitly; for real benchmarks, keep generated references and curation notes outside the agent-visible workspace.

## Required References

Read these files before extracting or reviewing a paper:

- `references/extraction_protocol.md`
- `references/quality_rubric.md`
- `schemas/reference_analysis_logic_chain.schema.json`

Use the bundled scripts for deterministic checks:

- `scripts/validate_reference_chain.py`
- `scripts/export_hypotrace_reference.py`

## Workflow

1. Identify the paper, data availability statement, public accessions, methods, figures, tables, and supplements.
2. Build the data backbone: modalities, datasets, samples, accessions, availability class, and reuse risks.
3. Set the analysis boundary: include agent-executable data analysis; move wet-lab, animal, clinical, therapeutic, or drug-delivery work into context.
4. Split the paper into connected chain questions, not figure sections.
5. Split each chain into intermediate analysis steps with enough scientific decision content to be useful for evaluation.
6. Separate `observed_evidence`, `analysis_result`, `biological_interpretation`, and `interpretation_boundary`.
7. Add short evidence anchors with source type, page/section/figure when available, anchor text, and evidence summary.
8. Validate the JSONL with `scripts/validate_reference_chain.py`.
9. Export HypoTrace draft references with `scripts/export_hypotrace_reference.py` when a demo or evaluator bundle needs `reference_*.json`.

## Output Contract

Write one JSONL file where each line is one intermediate analysis logic step:

```text
Paper -> Chain Question -> Connected Logic Steps
```

Each step must explain the evidence gap, analysis method, paper-reported evidence, analysis result, allowed biological interpretation, remaining uncertainty, and why the next step follows.

## Non-Invention Rules

- Do not invent accessions, sample counts, page numbers, methods, thresholds, markers, or claims.
- If a step is standard processing but not explicit in the paper, place it in `likely_default_processing` and use `step_origin: "inferred_default"` or `"mixed"`.
- Do not turn co-localization, enrichment, correlation, network prediction, ligand-receptor prediction, or regulon inference into causality.
- Do not require agents to reproduce the exact publication workflow when alternative methods can address the same evidence need.
- Do not expose hidden references, curation notes, rubrics, or evaluator prompts to the benchmark agent unless the task is explicitly a public full-gold demo.

## Quality Gate

A usable reference chain must have continuous `step_order` within each chain, correct `connects_from` and `connects_to`, a non-empty evidence anchor for each main step, an explicit interpretation boundary, and no non-analysis step in the connected main path.

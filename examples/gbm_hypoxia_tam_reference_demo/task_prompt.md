# Agent-Facing Task Prompt

You are given glioblastoma single-cell and spatial transcriptomics inputs related to tumor-associated myeloid states and tissue niches.

## Biological Question

Using the provided data, construct an evidence-grounded analysis trace that investigates whether a tumor-associated myeloid cell state can be defined from scRNA-seq, mapped into spatial glioblastoma tissue regions, and connected to candidate niche or communication factors.

## Available Inputs

- Human diffuse glioma scRNA-seq data or prepared single-cell objects.
- Public hGBM Visium spatial transcriptomics data or prepared spatial objects.
- Paired histology images or prepared spot-level histology annotations.
- Optional gene-set resources and public annotation files included in the task bundle.

The exact files and checksums are defined in `data_manifest.yaml`.

## Required Submission

Submit a HypoTrace-compatible output package containing:

- `trace_manifest.json`
- `scientific_chain.jsonl`
- `execution_subchains.jsonl`
- `artifacts.jsonl`
- `final_claims.json`
- `final_report.md`

Each scientific unit should state the question, evidence need, method intent, computational observation, biological inference, scope, and next question.

## Permitted Assumptions

- You may use reasonable bioinformatics alternatives when the exact publication method is unavailable, as long as the evidence need is addressed and limitations are stated.
- You should separate computational observations from biological interpretations.
- You should not claim causality from clustering, enrichment, spatial co-localization, correlation, ligand-receptor prediction, or network inference alone.
- You should document missing data, failed methods, and uncertainty instead of inventing results.

## Visibility Boundary

This task prompt intentionally omits hidden evaluator materials, gold chains, curator-only review files, and scoring instructions.

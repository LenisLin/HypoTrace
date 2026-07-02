# Extraction Protocol

## Purpose

Construct evaluator-only reference anchors from papers. The result is a reference chain, not the agent's execution trace and not a unique ground truth workflow.

The target user is a reference curator. The generated material must not be copied into an agent-facing benchmark prompt or starter workspace.

## Boundary

Include:

- data intake, QC, normalization, integration, clustering, annotation
- spatial mapping, deconvolution, domain analysis, region assignment
- differential expression, enrichment, gene set scoring, trajectory, network, communication, candidate prioritization
- paper-reported computational results and their evidence anchors

Exclude from the main method path:

- any non-computational validation step
- animal experiments, organoid experiments, perturbation assays, or wet-lab assays
- clinical outcome claims not directly derived from the computational analysis step
- drug delivery or therapeutic efficacy experiments
- mechanistic claims unsupported by the data-analysis evidence

Excluded items may be recorded in `article_context_after_analysis` when they explain how the paper continues after the analysis. They must not become connected main-chain steps unless the benchmark task explicitly asks for non-computational evidence curation.

## Step Granularity

Use intermediate tasks:

- Too small: one API call, one plot command, one package function with no scientific decision.
- Good: QC and object boundary definition; cluster marker detection; spatial deconvolution; region-level enrichment; ligand-receptor candidate map.
- Too large: "identify Hypoxia-TAM", "analyze spatial transcriptomics", "validate mechanism".

## Evidence Separation

- `observed_evidence`: data facts reported by the paper.
- `analysis_result`: analysis object or result derived from evidence.
- `biological_interpretation`: constrained biological reading of the result.
- `interpretation_boundary`: what cannot be concluded from this step.

Do not place biological interpretation in `observed_evidence`. For example, "cluster X up-regulates ADM/BNIP3/CSTB" is evidence; "cluster X is Hypoxia-TAM" is interpretation supported by marker/pathway evidence.

## Reference vs Agent Chain

Publication-derived reference chains are used to evaluate whether an agent covers critical scientific chokepoints. They should not require exact method duplication when alternative methods can support the same claim.

## HypoTrace Merge Boundary

- Git-visible HypoTrace material should contain task registry metadata, prompt, data manifest, schemas, and protocol docs.
- Full reference chains, hidden rubrics, and reference outputs belong in evaluator-only storage or the NAS task bundle.
- A publication-derived reference chain is a scientific anchor, not an exact workflow requirement.
- When exporting to HypoTrace draft files, keep `reference_only_not_ground_truth` or equivalent markers.

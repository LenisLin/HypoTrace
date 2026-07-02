# GBM Hypoxia-TAM Reference Curation Notes

Visibility: public_demo / full_gold_reference_demonstration

## Paper

- title: Identification of hypoxic macrophages in glioblastoma with therapeutic potential for vasculature normalization
- paper_id: GBM_HYPOXIA_TAM_2024
- domain: spatial_transcriptomics
- assay types: scRNA-seq, Visium, histology, bulk RNA-seq
- source locator: paper title: Identification of hypoxic macrophages in glioblastoma with therapeutic potential for vasculature normalization; public accessions: NGDC PRJCA008116 / OMIX002713, GEO GSE194329, OMIX003593
- public demo reference JSONL: examples/gbm_hypoxia_tam_reference_demo/analysis_logic_chain.jsonl

## Data Availability

- reported accessions: NGDC PRJCA008116 / OMIX002713, GEO GSE194329, OMIX003593
- reusable data status: reusable_data_ready
- bundle preparation status: not packaged as a HypoTrace NAS task bundle
- remaining data risks:
  - download URLs, checksums, sample metadata, and license/access notes still need bundle-level verification
  - public Visium sources and human glioma scRNA-seq sources should be pinned to exact files before benchmark release
  - the current demo validates reference extraction shape, not full runnable task reproducibility

## Reference Chain Summary

- C1: scRNA-seq -> Hypoxia-TAM state
  - 7 intermediate steps covering QC/object boundary, batch correction, clustering, marker detection, core signature construction, GSVA annotation, and Hypoxia-TAM state naming.
- C2: Mo-TAM state -> spatial niche
  - 6 intermediate steps covering Visium preprocessing, spatial deconvolution, Mo-TAM proportion estimation, histology-region assignment, and region-level enrichment.
- C3: Hypoxia-TAM -> ADM candidate prioritization
  - 5 intermediate steps covering hypoxia-associated gene construction, STRING/DAVID/Cytoscape network support, SCENIC regulons, CellPhoneDB communication candidates, and ADM prioritization.

## Boundary Decisions

- Included computational steps:
  - data preprocessing, object definition, integration, clustering, annotation, spatial mapping, deconvolution, enrichment, network/regulon inference, ligand-receptor analysis, and candidate prioritization.
- Excluded non-computational validation context:
  - Adm cKO xenograft, endothelial assays, AMA rescue, drug delivery, survival readouts, and therapeutic efficacy experiments.
- Rationale:
  - These downstream sections explain how the paper validates the ADM hypothesis, but they are not agent-executable data-analysis steps.
  - They can be referenced as article context after analysis, but must not be connected as reusable method-chain steps.

## Review Notes

- Evidence/result/interpretation separation:
  - observed evidence should stay close to reported data facts, such as marker expression, GSVA score patterns, Cell2location proportions, region labels, or candidate intersections.
  - analysis result should describe the analysis object or computed outcome.
  - biological interpretation should state the constrained paper-supported meaning.
- Overclaim risks:
  - UMAP clusters are not automatically biological states.
  - marker/pathway enrichment does not prove function.
  - spatial co-localization and region enrichment do not prove causality.
  - STRING, SCENIC, and CellPhoneDB are computational support, not direct physical or regulatory validation.
  - ADM prioritization is not causal proof without the downstream experimental context.
- Items needing PDF re-check before gold promotion:
  - exact PDF page anchors may differ from journal page labels.
  - data availability accessions should be cross-checked against the final publisher version and repository records.
  - evidence anchors currently use short locator strings and should be verified against the PDF text layer before locked evaluator release.

## HypoTrace Packaging Notes

- Git-visible files:
  - task_manifest.yaml, task_prompt.md, data_manifest.yaml, README.md, public protocol docs, schemas, and lightweight registry metadata.
- Gold/reference files included in this public demo:
  - reference_scientific_chain.json
  - reference_claim_surface.json
  - reference_execution_chain.json
  - curation_notes.md
  - quality rubric and evaluator prompts
  - any full extracted reference JSONL
- Agent-visible files:
  - task prompt
  - data manifest with visible data locators/checksums
  - prepared/raw data allowed for the task
  - HypoTrace output contract and templates
  - optional non-answer starter scripts or notebooks

## Promotion Checklist

- [x] schema valid
- [x] chain continuity valid
- [x] evidence anchors present for each main-chain step
- [x] hidden-reference boundary documented
- [ ] data bundle downloaded and checksummed
- [ ] exact source files mapped into a task data manifest
- [ ] PDF anchor text rechecked against final text layer
- [ ] human reviewer signs off that the chain is not over-claiming causality
- [ ] for real benchmarks, hidden reference files stored outside the agent-visible workspace

# ST Source Screening Round 1

This document records the source-screening order for the first HypoTrace ST task-definition discussion. It is a working discussion record, not a frozen task registry.

## Scope

This round is limited to spatial transcriptomics and closely related ST analysis tasks. Task levels, final task schema, and hidden reference structure are deferred until concrete examples are selected.

The canonical route for public-data research cases is [Public-Data Research Case
Extraction](public-data-research-case-extraction.md). This screening document
records source status and candidate pools; it does not duplicate that route.

## Discussion Order

1. Benchmark-derived sources
2. Bioinformatics tool paper sources
3. Database-supported biomedical research paper sources

## Benchmark-Derived Sources

| Source | Link | Current status | Round-1 decision |
|---|---|---|---|
| BixBench | https://github.com/Future-House/BixBench ; https://huggingface.co/datasets/futurehouse/BixBench | excluded from current ST round | Current screening did not identify ST-specific task/data support. Do not use as a Round-1 ST source unless later evidence identifies explicit spatial transcriptomics cases. |
| BioAgent Bench | https://github.com/bioagent-bench/bioagent-bench | excluded from current ST round | Current screening did not identify ST-specific task/data support. Do not use as a Round-1 ST source unless later evidence identifies explicit spatial transcriptomics cases. |
| SpatialBench | https://github.com/latchbio/spatialbench | screened; limited public-data route | Public examples are visible, but most benchmark data are exposed through `latch://` nodes rather than independently localizable public raw data. The only retained public-data-confirmed sources from this route are moved to the research-paper/database section below. |
| SpatialBench-Long | https://github.com/latchbio/spatialbench-long | screened; paper-linked route only for most cases | Public evals are visible, but current screening did not confirm complete public raw ST data entries for most cases. Paper-identifiable cases are moved to the research-paper/database section below as `paper-linked; public raw ST data unresolved`. |

### Benchmark Route Closure

Round-1 benchmark-derived screening is closed. It contributes only two public-data-confirmed source groups for downstream ST task consideration:

1. Visium bone: `GSE284089`.
2. Xenium / Visium kidney IRI: `GSE269719`, `GSE269622`, PubMed `40813851`, DOI `10.1038/s41467-025-62599-9`.

Other screened SpatialBench / SpatialBench-Long cases are not kept as standalone benchmark-source cases in this document. If the original paper can be identified but public raw ST data remain unresolved, the case is tracked only in the research-paper/database section. Benchmark trajectories, graders, `latch://` nodes, and public eval answers must not be treated as HypoTrace reference anchors.

## Tool / Method Paper Sources

This section is a source-pool overview only. Tool/method case extraction rules,
case-record templates, and NAS storage conventions are defined in
`tool-method-case-extraction.md`. Concrete extracted cases should be stored under
the NAS source-screening layout, organized by method, not embedded in this Git
source overview.

| Tool | Link | Current status | Notes |
|---|---|---|---|
| RCTD | https://doi.org/10.1038/s41587-021-00830-w | candidate | Deconvolution / cell-type mixture source. |
| COMMOT | https://doi.org/10.1038/s41592-022-01728-4 | candidate | Spatial cell-cell communication source. |
| FLOWSIG | https://doi.org/10.1038/s41592-024-02380-w | candidate | Intercellular flow inference source. |
| STAGATE | https://doi.org/10.1038/s41467-022-29439-6 | candidate | Spatial domain identification source. |
| STAligner | https://doi.org/10.1038/s43588-023-00528-w | candidate | Spatial dataset integration/alignment source. |
| STARFISH | https://doi.org/10.21105/joss.02440 | candidate | Image-based transcriptomics pipeline source; should be handled separately from Visium-style ST. |
| SLAT | TODO | unverified | Needs DOI, repository, or full name before inclusion. |

## Database-Supported Biomedical Research Paper Sources

The active first-round public-data source is STOmicsDB/STDS. Its case route is
defined in [Public-Data Research Case
Extraction](public-data-research-case-extraction.md), including the
article-anchored scope and public-access boundary.

| Source | Link | Current status | Notes |
|---|---|---|---|
| STOmicsDB / STDS | [canonical public-data route](public-data-research-case-extraction.md) | selected for active Round-1 intake | Screen article-anchored, anonymously public cases through the canonical route. |
| 10x Genomics official datasets | https://www.10xgenomics.com/datasets | deferred from active Round-1 intake | Retain as a future data-access route; do not add cases to the current intake. |
| CROST | not yet selected | deferred from active Round-1 intake | Retain for later source assessment; do not add cases to the current intake. |
| CRC CMS ST paper | https://doi.org/10.1038/s41698-023-00488-4 | high-priority candidate | Data/code available via Zenodo and GitHub; discuss after benchmark and tool-paper routes. |
| Spatial multi-modal atlas of bone tissue from human femur | https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE284089 | confirmed public data; localized | Identified through SpatialBench screening and retained here as a research/database source. GEO raw tar localized at `/mnt/NAS_21T/ProjectData/HypoTrace_Data/public_raw_data/GSE284089/GSE284089_RAW.tar`; BioProject `PRJNA1196981`. |
| Multimodal spatial transcriptomic characterization of mouse kidney injury and repair | https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE269719 ; https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE269622 ; https://doi.org/10.1038/s41467-025-62599-9 | confirmed public data; localization pending | Identified through SpatialBench screening and retained here as a research/database source. Xenium `GSE269719` and Visium `GSE269622` both map to PubMed `40813851`. |
| In situ multi-modal characterization of pancreatic cancer reveals tumor cell identity as a defining factor of the surrounding microenvironment | https://doi.org/10.1016/j.celrep.2025.116827 | paper-linked; public raw ST data unresolved | Identified through SpatialBench-Long screening. Keep as a research-paper candidate only until complete public raw ST data access is verified. |
| Genetically Engineered Brain Organoids Recapitulate Spatial and Developmental States of Glioblastoma Progression | https://doi.org/10.1002/advs.202410110 | paper-linked; public raw ST data unresolved | Identified through SpatialBench-Long screening. Exact public Xenium data source still needs verification before task extraction. |
| Spatiotemporal lineage tracing reveals the dynamic spatial architecture of tumour growth and metastasis | https://doi.org/10.1101/2024.10.21.619529 | paper-linked; public raw ST data unresolved | Identified through SpatialBench-Long screening. Also involves lineage tracing; retain only if the ST task scope accepts ST plus lineage integration. |
| Microglia activation orchestrates CXCL10-mediated CD8+ T cell recruitment to promote aging-related white matter degeneration | https://doi.org/10.1038/s41593-025-01955-w ; https://doi.org/10.5281/zenodo.15064255 | paper-linked; public raw ST data unresolved | Identified through SpatialBench-Long screening. Zenodo record is software only by current API check; raw MERFISH data availability remains unresolved. |

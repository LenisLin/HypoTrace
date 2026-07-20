# Discussion Framework

This document is navigation for the current HypoTrace design discussions. It is
not a contract and does not repeat route architecture defined in the dataset
documents.

## Core Corrections

ST round 1 starts from source-route screening, not from task levels, schemas,
benchmark conditions, or evaluator design. The current public-data route starts
with STOmicsDB/STDS and is defined in [Public-Data Research Case
Extraction](../datasets/public-data-research-case-extraction.md).

## Discussion Order

1. ST round 1 starts from source-route screening, not from task levels.
2. Review benchmark-derived sources:
   - SpatialBench
   - SpatialBench-Long
   - BixBench
   - BioAgent Bench
3. Review bioinformatics tool-paper sources:
   - RCTD
   - COMMOT
   - FLOWSIG
   - STAGATE
   - STAligner
   - STARFISH
   - SLAT
4. Review database-supported biomedical research papers through the canonical
   public-data route. STOmicsDB/STDS is active in Round 1; 10x and CROST are
   deferred from active intake.
5. After source-route screening, define candidate demo examples.
6. Only after concrete examples are selected, discuss task truncation, reference anchors, trace granularity, and level assignment.

## Canonical Documents

- [ST Source Screening Round 1](../datasets/st-source-screening-round1.md):
  current source status and candidate pool.
- [Public-Data Research Case
  Extraction](../datasets/public-data-research-case-extraction.md): public-data
  research-case route and source boundary.
- [Tool / Method Case Extraction](../datasets/tool-method-case-extraction.md):
  tool- and method-paper route.
- [Dual Chain Extraction](../datasets/dual-chain-extraction.md): shared
  case-derived chain procedure.
- [Data Contract](../datasets/data-contract.md): NAS and localization boundary.

## Deferred Topics

The following topics are intentionally deferred until concrete ST examples are selected:

- final task object schema and Level 1/2/3 assignment;
- task truncation, reference-anchor, and trace-granularity rules;
- evaluator layers, benchmark scoring, and pilot packaging;
- detailed public-data manifests, statuses, and executable procedures.

## External References To Review

The following references are relevant candidates for later formal review and citation. They should be verified before being used as factual support in frozen project documentation.

- SpatialBench-Long
- BioDSBench
- CellVoyager
- OmicOS
- BioAgent Bench
- BixBench

## Boundary

Dataset-route decisions belong in `docs/datasets/`; output contracts belong in
`contracts/`; benchmark and evaluation decisions belong in their respective
documentation. Hidden references, truth files, raw data, trajectories, and run
outputs remain outside Git.

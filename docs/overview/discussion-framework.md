# Discussion Framework

This document records the working order for upcoming HypoTrace design discussions. It is not a frozen contract. Decisions confirmed here should later be localized into dataset documentation, contracts, benchmark design, experiment configuration, or evaluator documentation.

## Core Corrections

ST round 1 starts from source-route screening, not from task levels, task schemas, benchmark conditions, or evaluator design.

This step records discussion order and the current reference pool. It does not define the final task object, Level 1/2/3 boundaries, hidden reference structure, or benchmark scoring design.

## Terms

The following terms are discussion placeholders. They are not final schema fields.

`Task object`: the eventual HypoTrace evaluation unit assigned to an agent.

`Task source`: the origin of a task, such as a public dataset, benchmark study, tool paper, or biomedical analysis paper.

`Reference anchor`: hidden evaluator-facing reference material used to interpret and score submissions. It is not a single mandatory ground truth trajectory.

`Submission contract`: the shared HypoTrace output format that every condition must use.

## Discussion Order

1. ST round 1 starts from source-route screening, not from task levels.
2. Discuss `benchmark_research` first:
   - SpatialBench
   - SpatialBench-Long
   - BixBench
   - BioAgent Bench
3. Discuss `bioinformatics_tool_paper` next:
   - RCTD
   - COMMOT
   - FLOWSIG
   - STAGATE
   - STAligner
   - STARFISH
   - SLAT
4. Discuss database-supported biomedical research papers last:
   - 10x Genomics official downloadable datasets as data-access entry points
   - CROST and STOmics to be added later
   - "Profiling the heterogeneity of colorectal cancer consensus molecular subtypes using spatial transcriptomics"
5. After source-route screening, define candidate demo examples.
6. Only after concrete examples are selected, discuss task truncation, reference anchors, trace granularity, and level assignment.

## Source Routes

HypoTrace currently treats source route as metadata rather than as the primary task type.

The four source routes are:

- `public_dataset`
- `benchmark_research`
- `bioinformatics_tool_paper`
- `biomedical_analysis_paper`

For ST round 1, source routes are discussed category by category. The project should not impose a universal per-case extraction table before the benchmark, tool-paper, and database-supported paper routes have each been examined.

For each route, the immediate goal is limited to:

- confirm concrete references and links;
- determine whether the source contains ST-relevant material;
- check whether data access is sufficient for a future demo;
- identify which examples should be discussed next.

## Deferred Topics

The following topics are intentionally deferred until concrete ST examples are selected:

- final task object schema;
- Level 1/2/3 assignment;
- task truncation rules;
- reference anchor structure;
- expected trace granularity;
- evaluator layers and benchmark scoring;
- pilot packaging workflow.

## Git And NAS Boundary

Git should store lightweight registry entries, task metadata, schema or contract references, curation status, checksums, license notes, and review status.

NAS should store complete task bundles, raw or processed data, hidden references, starter workspaces, runtime outputs, trajectories, and evaluator outputs.

Hidden references, truth files, large datasets, and run outputs must not be stored in the Git repository.

## External References To Review

The following references are relevant candidates for later formal review and citation. They should be verified before being used as factual support in frozen project documentation.

- SpatialBench-Long
- BioDSBench
- CellVoyager
- OmicOS
- BioAgent Bench
- BixBench

## Localization Rule

Confirmed task object and reference anchor decisions should move into `docs/datasets/`.

Confirmed output contract decisions should move into `contracts/`.

Confirmed benchmark condition and run-flow decisions should move into `docs/benchmark/` and `experiments/`.

Confirmed evaluator and metric decisions should move into `docs/evaluation/`.

## Constraints

Do not introduce version-numbered filenames for this discussion framework.

Do not add a new root-level `specs/` directory in this step.

Do not change existing loader, runner, evaluator, or schema behavior in this step.

Do not store hidden references, truth files, raw datasets, trajectories, or run outputs in Git.

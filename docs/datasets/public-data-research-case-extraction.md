# Public-Data Research Case Extraction

## Purpose

This document is the canonical route for constructing a HypoTrace public-data
research case. It covers the link from a public database record to a
paper-anchored scientific case. It does not define a task registry, hidden
reference material, a runnable workflow, or a new data contract.

## Research Case Unit

A public-data research case is one bounded scientific-analysis unit anchored to
one primary research paper and one or more public dataset records that support
that paper's stated analysis context. The case is not a database entry, a whole
dataset, or a paper abstract. It records the selected scientific question,
article scope, and public-data linkage needed to later curate a dual chain.

## Entities And Linkage

- A **database** is a public discovery or access service. It supplies records;
  it is not itself a case.
- A **dataset** is a data record or set of records exposed by a database. It can
  be associated with multiple papers or cases.
- A **paper** is a research article. The primary paper supplies the scientific
  context for a selected case.
- A **case** is the bounded paper-and-data analysis unit admitted to this route.
  It can use one or more dataset records and must name one primary paper.
- A **dual chain** is a later curation artifact for an admitted case. It uses the
  shared scientific-chain and execution-subchain rules; it is neither a gold
  trajectory nor an input to the agent.

The linkage record must make the database-to-dataset-to-primary-paper-to-case
relationship inspectable. A database link without an identified primary paper,
or a paper without a defensible public-data link, is not sufficient to define a
case.

## Admission Closures

Each candidate is evaluated for three closures before it is admitted for later
case extraction.

### Linkage Closure

The selected database record, dataset identity, primary paper, and case scope
are linked without relying on inference from a title alone. The record should
allow a reviewer to determine why the data belong to the selected paper and
why the selected case is a bounded use of those data.

### Scientific-Scope Closure

The primary paper anchors the research question, biological system, data use,
and analysis context. A case states only the scope supported by its selected
source material. It does not promote an article conclusion to ground truth or
extend the case to unrelated data or results.

### Localization And Execution Closure

The source material and the public data route are sufficiently identifiable for
later localization and case-level execution planning. This closure asks whether
the necessary materials can be reached and inspected; it does not prescribe a
specific processing pipeline, executable command, manifest format, or run
status.

## Generic Workflow

1. Discover candidate public records through a database.
2. Identify a dataset record and its associated primary research paper.
3. Bound a research case to a specific scientific question and paper-supported
   analysis context.
4. Check linkage, scientific-scope, and localization/execution closure.
5. Hand an admitted case to the shared data-localization and dual-chain
   procedures.
6. Defer task packaging, hidden references, and benchmark admission until their
   separate decisions are made.

## First-Round Source Profile: STOmicsDB And STDS

STOmicsDB is the selected public-data source for first-round intake. STDS
records are used as the source profile for discovering candidate spatial
transcriptomics datasets and their linked research context. Intake remains
article-anchored: a record becomes a candidate only after a primary paper and a
bounded research case can be identified.

First-round screening accepts only anonymous-public access routes: a curator
must be able to inspect the relevant public record and data-access route without
an account, institution-specific authorization, or a project invitation.
CNP/Project routes that require restricted access are outside active first-round
intake. Their existence may be noted as an access boundary, but they do not
close a public-data case.

## Data-Root Boundary

The following separation is conceptual and follows the existing data contract:

- `raw/public_database/` holds immutable downloaded or externally supplied
  public-database input material.
- `raw_data/public_database/` holds pre-task source-screening and curation
  material for public-database research cases.

No new shared data layout, manifest, or runtime artifact is introduced here.
The definitive NAS rules remain in [Data Contract](data-contract.md).

## Shared Procedures

An admitted case reuses [Data Contract](data-contract.md) for localization,
storage, and Git/NAS boundaries. It reuses [Dual Chain
Extraction](dual-chain-extraction.md) for case-derived scientific and execution
chains. This route does not duplicate either document.

## Deferred Decisions

The following are intentionally unresolved: detailed per-case manifest fields,
curation statuses, exact localization checks, executable analysis procedures,
task-package admission, hidden-reference design, and benchmark evaluation.

# Public-Data Research Case Extraction

## Purpose

This document is the canonical route for constructing a HypoTrace public-data
research case. It covers the link from a public database record to a
paper-anchored scientific case. It does not define a task registry, hidden
reference material, a runnable workflow, or a new data contract.

## Research Case Unit

A public-data research case is a localized public dataset slice with verified
paper/sample linkage, a bounded article-specific scientific result scope,
source-supported result material, and a reconstructable execution route. The
case is not a database entry, dataset, paper, figure, accession, portal-native
analysis, or whole-paper reproduction.

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

The linkage record must make the database, dataset, primary paper,
sample/section, accession, file/object, and case relationships inspectable. A
database link without an identified primary paper, or a paper without a
defensible public-data link, is not sufficient to define a case.

## Admission Closures

Each candidate is evaluated for three closures before it is admitted for later
case extraction.

### Linkage Closure

The selected database record, dataset identity, primary paper, sample or
section, accession, file or object, and case scope are linked through
inspectable relationships. Title similarity alone is insufficient. The record
should allow a reviewer to determine why the data belong to the selected paper
and why the selected case is a bounded use of those data.

### Scientific-Scope Closure

The primary paper anchors the research question, biological system, data use,
and analysis context. A case states only the scope supported by its selected
source material. It does not promote an article conclusion to ground truth or
extend the case to unrelated data or results.

When a paper integrates multiple modalities, retain only a public-data subset
that forms an independent scientific unit. Claims that require missing
modalities, unavailable patient-level metadata, perturbation evidence, or other
unavailable inputs must be narrowed or excluded and must not be inherited by
the case.

### Localization And Execution Closure

The source material and the public data route are sufficiently identifiable for
later localization and case-level execution planning. This closure asks whether
the necessary materials can be reached and inspected; it does not prescribe a
specific processing pipeline, executable command, manifest format, or run
status.

Required public objects may come from STOmicsDB or verified article-linked
public repositories. Alternative public objects require sample/object identity
verification, and access controls are not bypassed. Restricted CNP/Project
archives may be recorded as provenance but cannot close the case. If an
essential object is unavailable, the case scope must be narrowed or the case
must be rejected.

## Generic Workflow

1. Discover candidate public records through a database.
2. Identify the dataset, sample or section, accession, file or object, and
   associated primary research paper relationships.
3. Decompose the paper's result dependencies and bound an independent
   scientific unit with source-supported result material.
4. Admit the case only after linkage, scientific-scope, and
   localization/execution closure are satisfied.
5. Localize the admitted case's verified source and data objects.
6. Hand the admitted and localized case to the shared dual-chain extraction and
   independent-check procedures.
7. Defer task packaging, hidden references, and benchmark admission until their
   separate decisions are made.

## First-Round Source Profile: STOmicsDB And STDS

STOmicsDB is the selected public-data source for first-round intake. STDS means
a STOmicsDB Dataset record and is only a discovery identity. Portal metadata
supports discovery and linkage; it is not scientific result evidence.
Portal-native cases and downstream reuse papers are excluded. Only verified
primary/originating biomedical research articles enter first-round intake, and
a record becomes a candidate only after such a paper and a bounded research
case can be identified.

First-round screening accepts only anonymous-public access routes: a curator
must be able to inspect the relevant public record and data-access route without
an account, institution-specific authorization, or a project invitation.
CNP/Project routes that require restricted access are outside active first-round
intake. Their existence may be noted as an access boundary, but they do not
close a public-data case.

## Data-Root Boundary

The following source-specific layout is conceptual and follows the existing
data contract:

```text
raw/public_database/<source>/
raw_data/public_database/<source>/
  registry/
  datasets/
  papers/
  cases/
```

`raw/public_database/<source>/` holds immutable downloaded or externally
supplied public-database input material. Within
`raw_data/public_database/<source>/`, `registry/` records intake, linkage, and
admission state; `datasets/` holds shared dataset, sample, and file assets;
`papers/` holds localized article and source packages; and `cases/` holds
paper-specific bounded slices.

No new shared data layout, manifest, or runtime artifact is introduced here.
The definitive NAS rules remain in [Data Contract](data-contract.md).

## Shared Procedures

An admitted case reuses [Data Contract](data-contract.md) for localization,
storage, and Git/NAS boundaries. It reuses [Dual Chain
Extraction](dual-chain-extraction.md) for case-derived scientific and execution
chains. This route does not duplicate either document.

`method_slug`, method-level screening, and tool/method case-reference reuse do
not define this route.

## Deferred Decisions

The following are intentionally unresolved: linkage and manifest fields, case
ID syntax, derived-information materialization, runnable validation, exact
Stage numbering, pilot admission, batch orchestration, task-package admission,
hidden-reference design, and benchmark evaluation.

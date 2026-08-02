# Public-Data Research Case Extraction

## Purpose

This document is the canonical route for constructing a HypoTrace public-data
research case. It covers the link from a public database record to a
paper-anchored scientific case. It does not define a task registry, hidden
reference material, or a runnable workflow.

The active STOmicsDB research scope is frozen to exactly the following 16 STDS
records. Only these records may remain in active registries, dataset packages,
paper linkages, dispatch inputs, and downstream case construction.

```text
STDS0000001
STDS0000007
STDS0000066
STDS0000073
STDS0000081
STDS0000089
STDS0000091
STDS0000106
STDS0000124
STDS0000162
STDS0000181
STDS0000182
STDS0000201
STDS0000212
STDS0000217
STDS0000227
```

The ordered `selected_stds_ids` field in the current STOmicsDB intake manifest
must match this list exactly. A scope change requires an explicit replacement
decision; discovery results or historical intake state do not expand the
active scope.

## Research Case Unit

One Round 3 job binds one dataset-local article to one STDS dataset. The job may
produce zero, one, or multiple case candidates. A candidate contains one
spatial result or an ordered connected group of spatial results supported by
the assigned dataset.

A result is defined by one Results-section scientific question, conclusion,
one or more main-article figure, table, or stable text anchors, and ordered
analysis steps. The article is read in full, but Round 3 result enumeration
excludes supplementary-only analyses.

A logical scientific dataset is one coherent analysis input with a consistent
assay identity and compatible sample coverage. Its paired expression,
coordinates, image, and metadata are components of one logical object even when
they occupy multiple files, archives, bundles, or sample directories. A
separate assay, reference dataset, or scientifically distinct input is a
separate logical object. File boundaries alone do not define scientific dataset
boundaries.

Portal linkage and dataset-local article presence establish an input
relationship, not scientific support. Scientific support is determined case by
case from the result's declared inputs and the actual canonical data
representation.

A candidate is not an entire paper, database record, figure collection, or
exhaustive analysis route. A candidate does not require maximal connectedness.
Multiple results belong together only when they use the same primary logical
spatial dataset, have compatible assay and sample scope, preserve scientific
order, and an upstream analysis output is an explicit downstream analysis
input. This same-data stitching rule permits different reference data or
auxiliary resources but never joins independent results merely because they
occur in the same article or use related files. Null, non-significant, or
unfavorable findings remain valid when source-supported. Producing no candidate
(`no_candidate`) is a valid scientific outcome and is not an execution failure.

## Evidence Distinctions

Round 3 process reasoning distinguishes:

```text
evidence_insufficient
resource_identified_but_not_directly_downloadable
resource_not_required_by_the_retained_analysis
```

These meanings are mutually non-substitutable. They remain process reasoning
and are not formal output fields. In particular, inaccessible evidence does not
establish irrelevance, and a result direction does not determine eligibility.

## Generic Workflow

1. Bind the dataset-local article.
2. Read the complete article.
3. Apply the spatial-input filter.
4. Inspect relevant canonical data.
5. Search necessary auxiliary inputs.
6. Decide data support.
7. Construct case candidates.
8. Review and apply one targeted repair when needed.
9. Publish or return a terminal response.

The executable workflow defines role and return contracts. This semantic
document does not duplicate them.

## Data-Root Boundary

The [Data Contract](data-contract.md) is the sole owner of canonical physical
NAS locations and record ownership. This semantic contract does not duplicate
those paths.

## Shared Procedures

The [STOmicsDB Localization Workflow](stomicsdb-localization-workflow.md) owns
Round 1 discovery/localization, Round 1.5 acquisition planning, Round 2A
download, and Round 2B structural localization. The [STOmicsDB Case
Construction Workflow](stomicsdb-case-construction-workflow.md) owns the
executable Round 3 procedure. [Dual Chain
Extraction](dual-chain-extraction.md) owns downstream consumption.

## Downstream boundary

The five Round 3 role prompts, standalone checklist, and output template are
active contract authorities. Dual-chain extraction, task admission, hidden
references, and benchmark evaluation remain downstream.

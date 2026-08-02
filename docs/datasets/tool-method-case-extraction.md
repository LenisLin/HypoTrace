# Tool / Method Case Extraction

## Purpose

This document defines case-level extraction for ST tool/method papers and
official tutorials or examples. The extraction unit is a `tool/method case`:
one ST application case used to decide whether a tool/method-derived example
can support later chain and task construction.

This document does not define HypoTrace task levels, reference chains, execution
chains, claim surfaces, evaluator schemas, hidden references, truth files, or
benchmark trajectories.

After a case passes source screening and pre-chain localization, dual-chain
extraction is handled by `dual-chain-extraction.md`. Do not append scientific
or execution chains directly to the screening YAML.

## Unit Of Extraction

A tool/method case is one ST application case from a method paper or official
tutorial that uses real public data or tutorial data with a specific data object
that can be inspected.

It is not:

- a dataset
- a paper
- a figure
- a benchmark comparison
- a method call
- a final task
- a paper conclusion as ground truth

## Include / Exclude Rules

Include:

- biological application result sections that appear after algorithm development
  and benchmark sections in method papers
- case studies based on public data
- official GitHub, documentation, Read the Docs, or equivalent tutorial/example
  pages
- real-data demonstrations with explicit data objects

Exclude:

- motivation, model formulation, or algorithm development sections
- simulation-only examples
- benchmark-only comparisons
- ablation, runtime, ARI/NMI-only, or similar metric-only results
- workflows that only evaluate whether a tool was called

## Article Case vs Tutorial Case

Article case:

- usually comes from the later result sections of a method paper
- often contains a shallow biological story
- may include ST data, scRNA-seq references, metadata, and derived annotations
- treats paper claims as source information, not as ground truth

Tutorial case:

- comes from an official tutorial or example
- may have a shallow biological story
- is evaluated mainly for clear data objects and a reproducible access route
- should be marked as `case_depth: tutorial` and not mixed with article cases

## Workflow Stages

### Execution Unit Split

Stage 1 screening is method-level: one `method_slug` produces one
`screening.yaml`. Method-level orchestration reads every
`screening.yaml:cases[]` entry. Stage 2 localization is case-level: one
dispatch handles exactly one specified `case_id`, and every screened case must
end with `DATA_READY` or `BLOCKED_EXTERNAL`. Stage 3 extraction is
case-scoped and chain-targeted: one dispatch handles one `DATA_READY case_id`
and one target `dual_chain/<chain_id>/` directory. If one case needs multiple
independent chains, use separate target chain directories and dispatches. Stage
4 confirmation is chain-level: one dispatch confirms one generated
`dual_chain/<chain_id>/`.

### Method-Level Orchestration

After Stage 1, the main workflow treats `screening.yaml:cases[]` as the full
localization queue. It dispatches Stage 2 once for every case entry. Priority,
initial validation notes, or recommended order may affect execution order, not
coverage. After Stage 2, every `DATA_READY` case proceeds to Stage 3 with at
least one target chain directory. Stage 4 runs once for every generated
`dual_chain/<chain_id>/` directory.

### Registry-Scale Batch Orchestration

Registry-scale tool/method batches may group method-paper seeds into execution
batches. For the Layer1 ST method registry batch, the default batch size is ten
method seeds. Each method seed may be assigned to one method-level worker for
Stage 1-2 orchestration, while the canonical output units remain unchanged:
one method-level `screening.yaml`, one Stage 2 localization record per
`case_id`, one Stage 3 chain directory per approved `case_id` and `chain_id`,
and one Stage 4 confirmation per generated chain directory.

Registry-scale execution follows this order:

1. Run Stage 1-2 for all methods in the batch set.
2. Build a human-reviewed Stage 3 queue from Stage 2 outputs.
3. Run Stage 3 only for `DATA_READY` cases admitted by the human-reviewed queue.
4. Run Stage 4 after Stage 3 outputs have been generated.

`DATA_READY` is required for Stage 3 consideration, but it is not sufficient in
registry-scale batches. Human review may mark cases as entering Stage 3,
excluded from Stage 3, or deferred. These decisions are batch-management
records, not new manifest status values.

Batch-management records for the Layer1 ST method registry batch are stored
under `raw_data/tool_method/_registry_batches/layer1_tier_a_140/`.

### Stage 1. Tool/Method Case Screening

Stage 1 is method-level screening. It starts from a method or article seed and
writes one method-level `screening.yaml` under
`raw_data/tool_method/<method_slug>/screen/screening.yaml`. It localizes
screen-stage source files under `raw_data/tool_method/<method_slug>/source/`
and records package-level source acquisition in
`raw_data/tool_method/<method_slug>/source/source_manifest.yaml`.

1. Start from a method name, method article, DOI, implementation repository,
   documentation URL, or equivalent seed.
2. Search online for the method article, implementation repository, official
   documentation, tutorials, vignettes, examples, and notebooks.
3. Localize source material needed for case extraction: article PDF/text,
   repository README or indexes, documentation pages, tutorial pages,
   vignettes, examples, notebooks, and scripts. Do not localize raw data during
   screening.
4. Record package-level source acquisition in `source/source_manifest.yaml`.
5. Extract all source-level ST tool/method cases into `cases[]`. Each entry is
   keyed by `case_id`.
6. Fill `sources`, `coverage_notes`, and each case entry's `source`,
   `basic_info`, `data_slice.objects`, `data_access`, `scientific_cautions`,
   and `notes`.
7. Record source-level leads only. Keep raw data localization, scientific
   problems, HVUs, execution routes, data readiness, chain artifacts, and check
   artifacts out of method-level `screening.yaml`.

Weak data lead rule: article cases enter `cases[]` when there is an ST
application source locator and usable data leads, even if file-level artifacts
are unresolved.

`coverage_notes` is free text for included and skipped article sections,
tutorials, scripts, vignettes, examples, and reasons.

Package vignettes, examples, and documentation for the implementation package
count as `official_tutorial`. For RCTD, `spacexr` vignettes, examples, and
documentation count as official tutorial sources. Article and tutorial cases
using the same dataset are retained as separate cases. When retained cases use
the same underlying dataset, record a shared `dataset_group_id` or related case
note for leakage control.

### Stage 2. Pre-Chain Localization

Stage 2 runs for every case emitted by Stage 1 through one per-case dispatch.
Its fixed inputs are `method_screening_yaml`, `method_slug`, and `case_id`. It
reads the matching `cases[]` entry, applies the source coverage gate for the
specified case, localizes case-specific source material, and localizes case
data before dual-chain extraction. It writes three required case records plus
case-local data artifacts:

- `raw_data/tool_method/<method_slug>/cases/<case_id>/case_screen.yaml`
- `raw_data/tool_method/<method_slug>/cases/<case_id>/source_manifest.yaml`
- `raw_data/tool_method/<method_slug>/cases/<case_id>/data/case_data_manifest.yaml`
- `raw_data/tool_method/<method_slug>/cases/<case_id>/data/objects/<data_object_id>/`
- `raw_data/tool_method/<method_slug>/cases/<case_id>/data/samples/<sample_id>/`

Stage 2 remains chain-extraction-ready, not analysis-execution-ready.

#### Source Material Localization

1. Read method-level `screening.yaml`.
2. Select exactly one matching `cases[]` entry by `case_id`.
3. Write the selected `screening.yaml:cases[case_id]` entry to
   `case_screen.yaml`.
4. Read screen-stage source local paths listed under `sources` and classify
   the specified case as `article_case` or `official_tutorial` from
   `case_depth` and source type.
5. For `article_case`, confirm that the original article PDF and extracted
   article text are present in method-level or case-level source manifests.
   If either source is absent, localize it in the current Stage 2 dispatch.
6. For `article_case`, also localize the exact case-bearing source material:
   result section text when available, supplement, data availability text,
   figure/table source, notebook, script, repository file, or other localized
   source object used by the case. For `official_tutorial`, localize the exact
   tutorial, documentation, notebook, script, vignette, or example source used
   by the case.
7. Write every localized source object to `source_manifest.yaml` using roles
   already supported by the template, especially `paper_pdf`, `paper_text`,
   `supplement`, `data_availability`, `figure_table`, `notebook`, `script`,
   `vignette`, and `example`. Expand directory/index leads to exact source
   files when needed; a GitHub tree cannot be recorded as an `ipynb` unless a
   concrete notebook file is localized.

#### Case Data Localization

1. Read data leads from the specified `cases[]` entry and localized source
   material.
2. Check same-`method_slug` cases with matching `dataset_group_id` or
   `related_case_ids` for an existing `DATA_READY case_data_manifest.yaml`.
   Any candidate reused `case_data_manifest.yaml` must be YAML-parseable before
   reuse.
   When the source/data leads support the same data object, create a soft link
   in the current case's `data/` tree and record `reused_from_case_id`, link
   path, and target path in existing manifest fields.
3. Resolve concrete data routes for objects not already usable through
   Case-reference reuse using the route-completion classes in
   `docs/datasets/data-contract.md`: direct download, accession, portal/index,
   repository directory, package/helper route, existing NAS path, or
   notebook-derived lead.
4. If the first public route fails, perform one targeted online re-resolution
   using accession, DOI data availability, portal study ID, sample IDs, or file
   names before assigning `BLOCKED_EXTERNAL`.
5. For each required data object, enter an active localization loop:
   - retrieve, copy, or localize the artifact under the current case's
     `data/objects/<data_object_id>/` or `data/samples/<sample_id>/`;
   - resume or redownload incomplete artifacts when the route is reachable;
   - unpack, extract, load, or prepare archives and native containers in the
     case-local data tree when needed;
   - read or inspect enough structure to support Stage 3 use;
   - record local paths, local artifacts, read summary, ST data contract
     fields, sample structure, identifier checks, and remaining issues.
6. Continue the loop until the case reaches `DATA_READY` or a true external
   blocker prevents the next action.
7. Set final `case_data_manifest.data_localization_status` to `DATA_READY` or
   `BLOCKED_EXTERNAL`.

When Case-reference reuse is used, still write the current case's own
`source_manifest.yaml` and `case_data_manifest.yaml`. Record reuse in existing
fields such as `source_note`, `retrieval_attempts`, `local_artifacts`,
`read_summary`, `notes`, or `remaining_issue` as valid YAML free text,
preserving `reused_from_case_id`, the current-case soft link path, and the link
target path.

`DATA_REPAIR_REQUIRED` is an internal repair-loop condition and is not a final
`case_data_manifest.yaml:case_data_manifest.data_localization_status`.

Large reachable artifacts are attempted with resumable retrieval when possible;
file size or download duration alone is not a final blocker.

Before ending Stage 2 dispatch, parse `source_manifest.yaml` and
`case_data_manifest.yaml`; confirm
`case_data_manifest.data_localization_status` is `DATA_READY` or
`BLOCKED_EXTERNAL`; confirm `case_data_manifest.data_objects[].visibility`
uses only `agent_input_candidate`, `evaluator_context_only`, or
`excluded_derived_output`. Keep scientific/data descriptor fields human-readable
and do not force narrow platform or unit enumerations.

Every case with localized source material and
`case_data_manifest.yaml:case_data_manifest.data_localization_status:
DATA_READY` is eligible for dual-chain extraction. In direct per-method
curation, eligible cases may proceed to Stage 3. In registry-scale batches,
eligible cases enter the human-reviewed Stage 3 queue before extraction. Cases
with `BLOCKED_EXTERNAL` remain recorded at Stage 2 and do not proceed to Stage
3.

Subagent dispatch entry:
`contracts/prompts/curation/dispatch_tool_method_case_localization.md`.

### Stage 3. Dual-Chain Extraction

Dual-chain extraction starts after Stage 2. It consumes method-level
`screening.yaml`, `method_slug`, `case_id`, `case_screen.yaml`,
`source_manifest.yaml`, and `case_data_manifest.yaml`. Chain construction is
defined in `dual-chain-extraction.md`.

Subagent dispatch entry:
`contracts/prompts/curation/dispatch_dual_chain_extraction.md`.

### Stage 4. Chain-Independent Confirmation

Stage 4 reviews extracted chain artifacts after Stage 3. It reads the localized
source record, localized data record, chain manifest, scientific chain, and
execution subchains. It writes a per-chain Markdown checklist review at
`dual_chain/<chain_id>/independent_check.md`, then records summary status,
summary findings, and `notes_location` in
`chain_manifest.yaml:independent_check`. It does not edit
`scientific_chain.jsonl` or `execution_subchains.jsonl`.

Any human review loop occurs after independent confirmation, not before
screening or case extraction.

Subagent dispatch entry:
`contracts/prompts/curation/dispatch_dual_chain_independent_check.md`.

## Template

Use this empty YAML template for method-level source-screening records.
Extracted records are source-level curation artifacts and should be stored on
NAS, not in this Git repository.

```yaml
method_slug:
method_name:

sources:
  article:
    title:
    doi:
    url:
    local_path:
    format:
    notes:
  repository:
    url:
    local_paths:
      - path:
        role:
        format:
        notes:
  docs:
    entries:
      - url:
        local_path:
        role:
        format:
        notes:

coverage_notes: |

cases:
  - case_id:
    dataset_group_id:
    related_case_ids:
      -
    source:
      route: bioinformatics_tool_paper
      type: paper_case_section | official_tutorial
      tool:
      paper_or_doc:
      section_or_example:
      link:
      repository:
    basic_info:
      organism:
      tissue:
      context:
      case_depth: tutorial | article_case
      data_slice:
        objects:
          - id:
            role: spatial_expression | spatial_coordinates | histology_or_image | reference_expression | reference_labels | metadata | clinical_table | external_database | derived_metadata
            description:
            format:
    data_access:
      objects:
        - id:
          address:
          notes:
      unresolved:
    scientific_cautions:
      - paper conclusion is not ground truth
      - do not frame future task as reproducing a named figure or author claim
      - avoid causal or clinical claims unless design supports them
      - distinguish observed spatial association from mechanism
    notes:
      -
```

Use this empty YAML template for source localization records:

```yaml
source_manifest:
  case_id:
  method_slug:

  source_materials:
    - id:
      role: paper_pdf | paper_text | supplement | figure_table | data_availability | documentation_page | tutorial_page | repository_readme | notebook | script | vignette | example | download_log
      original_url:
      local_path:
      format:
      notes:

  source_acquisition:
    selected_paths:
      - local_path:
        source_role:
        original_url:
    repository:
    requested_paths:
      -
    retrieval_attempts:
      - target:
        method:
        status:
        notes:
```

Use this empty YAML template for case data localization records:

```yaml
case_data_manifest:
  case_id:
  method_slug:
  data_localization_status: DATA_READY | BLOCKED_EXTERNAL

  data_objects:
    - id:
      role: spatial_expression | spatial_coordinates | histology_or_image | reference_expression | reference_labels | metadata | clinical_table | external_database | derived_metadata
      visibility: agent_input_candidate | evaluator_context_only | excluded_derived_output
      source_address:
      source_note:
      retrieval_attempts:
        - target:
          method:
          status:
          notes:
      local_raw_path:
      prepared_path:
      prepared_format:
      checksum:
      local_artifacts:
        - path:
          role:
          format:
      read_summary:
      remaining_issue:
      notes:

  st_data_contract:
    platform_family: Visium | Xenium | Slide-seq | MERFISH | STARmap | Stereo-seq | other | unknown
    observation_unit: spot | cell | bead | bin | other | unknown
    coordinate_semantics:
    coordinate_unit_or_frame:
    coordinate_range:
    image_required: yes | no | unknown
    image_source:
    image_alignment_status: pass | fail | not_applicable | not_checked
    image_alignment_evidence:

  sample_structure:
    sample_count:
    section_count:
    patient_count:
    replicate_structure:
    grouping_variables:
    clinical_metadata_available:

  identifier_checks:
    spatial_expression_to_coordinates: pass | fail | not_applicable | not_checked
    spatial_expression_to_image_metadata: pass | fail | not_applicable | not_checked
    spatial_expression_to_reference_genes: pass | fail | not_applicable | not_checked
    reference_cells_to_labels: pass | fail | not_applicable | not_checked
    notes:

  repair_target:
  files_written:
    -
```

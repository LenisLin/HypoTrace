# Data Contract

The default data root is `/mnt/NAS_21T/ProjectData/HypoTrace_Data`.

Required subdirectories:

- `raw_data/`: canonical pre-task source-screening and tool/method curation
  packages, including screen, source, case data, and case-derived chain
  artifacts.
- `raw/`: immutable downloaded or externally supplied input data.
- `tasks/`: complete NAS task bundles keyed by task id.
- `references/`: hidden truth files, reference outputs, and evaluator-only anchors.
- `runs/`: per-run submissions, manifests, logs, artifacts, scores, and summaries.
- `trajectories/`: agent messages, tool calls, notebooks, or equivalent traces.
- `results/`: aggregated benchmark outputs.
- `logs/`: cross-run operational logs.

## Pre-task Source Screening Layout

Source-screening records and source-level curation artifacts are stored on NAS,
not in the Git repository. They are not task bundles and must not be treated as
hidden references or benchmark trajectories.

Tool/method paper screening is organized by method:

```text
/mnt/NAS_21T/ProjectData/HypoTrace_Data/
  raw_data/tool_method/<method_slug>/
    screen/
      screening.yaml
    source/
      source_manifest.yaml
      article_file
      repo/
      docs/
      supplements/
      download_log_file.log
    cases/
      <case_id>/
        case_screen.yaml
        source_manifest.yaml
        data/
          case_data_manifest.yaml
          objects/
            <data_object_id>/
          samples/
            <sample_id>/
              filtered_feature_bc_matrix.h5
              spatial/
        dual_chain/
          <chain_id>/
            chain_manifest.yaml
            scientific_chain.jsonl
            execution_subchains.jsonl
            independent_check.md
```

Method-level `screening.yaml` stores method source records, `coverage_notes`,
and `cases[]`. Later stages read `screening.yaml:cases[]` by fixed `case_id`.
Screening source files are referenced from `screening.yaml:sources` and should
resolve under `raw_data/tool_method/<method_slug>/source/` unless the source is
an external URL.
All local paths recorded in method-level `screening.yaml:sources` are
NAS-data-root-relative paths unless explicitly marked as external URLs.
Absolute local paths are discouraged because they reduce portability across
curation agents and machines.

The package-level `source/source_manifest.yaml` stores localized article,
repository, documentation, tutorial, and source evidence for the method/article
package. A per-case `source_manifest.yaml` stores the subset and additional
localized source material for one specified case. Its canonical location is
`raw_data/tool_method/<method_slug>/cases/<case_id>/source_manifest.yaml`.
`chain_manifest.yaml:source_manifest` should store this data-root-relative
path, not a copied manifest under the chain directory.

`case_data_manifest.yaml` stores case-level data localization, local or
case-prepared paths, read summaries, ST coordinate context, sample structure,
identifier checks, repair target, and data readiness status.

`dual_chain/<chain_id>/` stores case-derived dual-chain artifacts and the
Stage 4 independent-check review.

`chain_manifest.yaml` stores chain scope, used source material, used data
objects, data readiness summary, schema check references, independent-check
status, summary findings, and `notes_location`.

### Chain Data Object References

`chain_manifest.yaml:used_data_objects[].id` references
`case_data_manifest.yaml:case_data_manifest.data_objects[].id` by default.

When a chain needs an internal package artifact, R object, CSV, RData object,
notebook output, or another object inside a localized top-level data object,
record it as an artifact reference under the parent data object instead of as
an independent top-level data object. Recommended shape:

```yaml
used_data_objects:
  - id: <case_data_manifest_data_object_id>
    role: <object_role>
    artifact_refs:
      - name: <internal_artifact_or_object_name>
        role: <artifact_role>
        path_or_locator: <data-root-relative-path-or-source-locator>
    required_by_scientific_units:
      -
    required_by_execution_subchains:
      -
```

Do not write internal artifact names as bare independent top-level data object
IDs unless they are also registered as
`case_data_manifest.yaml:case_data_manifest.data_objects[]` entries. Stage 4
should mark a bare artifact name as `needs_revision` for reference expression.
This is not, by itself, a scientific-chain failure.

`independent_check.md` stores the detailed Stage 4 checklist review for one
chain.

### Engineering output classes

`screen/`: method/article-level screening output. Contains `screening.yaml` and
source-level case leads.

`source/`: localized article, repository, documentation, tutorial, and source
evidence. Contains source files and the package-level `source_manifest.yaml`.

`cases/<case_id>/case_screen.yaml`: case-specific slice extracted from
`screening.yaml`, not the full method screen.

`cases/<case_id>/data/`: localized case data and `case_data_manifest.yaml`.

`cases/<case_id>/dual_chain/<chain_id>/`: case-derived chain artifacts,
`chain_manifest.yaml` independent-check summary fields, and the detailed `independent_check.md` review.

These outputs are curation and intermediate engineering outputs for chain
extraction. They are not final benchmark task bundles.

### Case data layout

`cases/<case_id>/data/case_data_manifest.yaml` is the data localization record.

`cases/<case_id>/data/objects/<data_object_id>/` stores non-sample data objects
such as references, metadata tables, RDS files, H5AD files, MAT files, or
support archives.

`cases/<case_id>/data/samples/<sample_id>/` stores sample-level ST data. For
10x/Visium, the canonical localized sample unit is:

```text
samples/<sample_id>/
  filtered_feature_bc_matrix.h5
  spatial/
    tissue_positions_list.csv
    scalefactors_json.json
    tissue_hires_image.png
    tissue_lowres_image.png
    ...
```

The localized matrix does not have to be an H5 file when the source-supported
case data is provided in another inspectable format such as RDS, H5AD, MAT, or
a CSV directory. For 10x/Visium cases with raw sample components available,
`filtered_feature_bc_matrix.h5` plus `spatial/` is the canonical localized
input unit. A `.h5ad` file may be stored as an optional derived object, but it
should not be the only canonical localized input when source-supported raw
Visium components are available.

Shared data between cases should appear as a soft link in the current case's
`data/` tree and be recorded in `case_data_manifest.yaml` with the source case,
link path, and target path.

### Manifest write hygiene

YAML manifests must parse with a standard YAML parser after writing. Free-text
fields containing `:`, URLs, list-like text, or multiline notes should use
quoted strings or block scalars. If parsing fails, repair only YAML expression;
do not change paths, status, object identity, or scientific/data meaning.
Access limits, reuse insufficiency, unavailable objects, or repair needs belong
in free-text fields such as `source_note`, `retrieval_attempts.notes`,
`read_summary`, `remaining_issue`, `repair_target`, or `notes`. Final
`case_data_manifest.data_localization_status` values remain only `DATA_READY`
and `BLOCKED_EXTERNAL`. `case_data_manifest.data_objects[].visibility` uses
only `agent_input_candidate`, `evaluator_context_only`, or
`excluded_derived_output`; phrases such as required-but-unavailable or
reusable-but-insufficient belong in free-text fields.

Case data readiness check:

1. Read case data leads and localized source material.
2. Resolve each required object to direct download, accession, portal/index,
   repository directory, package/helper route, existing NAS path, or
   notebook-derived lead.
3. For accessions or landing pages, expand to concrete required artifacts.
4. For portals/indexes/GitHub directory leads, list candidate artifacts and
   record the selected artifact reason.
5. For notebook-local paths, use filenames, sample IDs, object names, and
   article data availability for one targeted online re-resolution.
6. If an exact derived artifact is unavailable but localized source material
   gives raw public data routes and construction logic, resolve the raw route
   and prepare a source-supported equivalent object before assigning
   `BLOCKED_EXTERNAL`. Record the rebuild route in existing fields
   (`retrieval_attempts`, `local_artifacts`, `read_summary`,
   `remaining_issue`, `repair_target`). This is data preparation, not
   dual-chain extraction.
7. For reachable concrete artifact routes, including existing NAS paths and
   package/helper outputs, download/localize, unpack/prepare when needed, and
   read enough structure for Stage 3.
8. Use `BLOCKED_EXTERNAL` only after the next action truly requires access,
   credentials, unavailable service, storage, or no public route after targeted
   re-resolution.

### Case-Reference Data Reuse

Tool/method case localization uses case-reference reuse instead of a shared
dataset directory. Do not add a new shared data path for this workflow, and do
not move existing case-localized artifacts. A case may reference another
case's local or prepared artifact when `dataset_group_id`, `related_case_ids`,
or source/data leads support reuse.

The current `case_data_manifest.yaml` must still record the source case,
object mapping, reused paths, and current-case read/context summary. Reused
artifacts should appear as soft links in the current case's `data/` tree.
Record `reused_from_case_id`, the current-case link path, the target path, and
the current-case read/context summary in existing manifest fields such as
`source_note`, `retrieval_attempts`, `local_artifacts`, `read_summary`, `notes`,
or `remaining_issue`. Reuse does not skip the current case's final
`case_data_manifest.data_localization_status`.

Data localization status values:

- `DATA_READY`: required case data objects have usable local/prepared artifacts
  and required read/context records.
- `BLOCKED_EXTERNAL`: the next required action needs access, credentials,
  unavailable service, missing public route, storage, or another condition
  outside the execution window.

`DATA_REPAIR_REQUIRED` is an internal repair-loop condition. It means the
workflow continues using existing fields such as `retrieval_attempts`,
`remaining_issue`, `repair_target`, `read_summary`, and `notes`; it is not a
final `case_data_manifest.data_localization_status`.

Both `source/source_manifest.yaml` and per-case `source_manifest.yaml` should
include a `source_acquisition` record. The default acquisition target is the
narrowest source scope that supports extraction: source documents or exact
tutorial, example, vignette, notebook, or script files. Complete repository
snapshots are outside the default tool/method case workflow.

```yaml
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

The package-local `screen/`, `source/`, `cases/<case_id>/data/`, and
`cases/<case_id>/dual_chain/` directories store source-level curation records,
localized source files, localized case data, chain curation artifacts, and
independent-check reviews for this workflow. These curator-facing files are not
copied into agent input by default.

Do not store raw data, hidden references, truth files, extracted trajectories,
or run outputs in Git.

## Run Layout

Each run should write to:

```text
runs/<task_id>/<run_id>/
  input/
    task_prompt.md
    HYPO_TRACE_SKILL.md
    output_template/
    data/
  agent_workspace/
  submission/
    trace_manifest.json
    scientific_chain.jsonl
    execution_subchains.jsonl
    artifacts.jsonl
    final_claims.json
    final_report.md
    workspace/
      scripts/
      notebooks/
      figures/
      tables/
      logs/
  logs/
    harness_stdout.log
    harness_stderr.log
    tool_calls.jsonl
    token_usage.json
    run_meta.json
  eval/
    validation_report.json
    trace_graph.json
    score_report.json
    metric_table.csv
    evaluator_notes.md
```

The `submission/` directory is the common output protocol shared by all
model-harness-conditions and is the agent submission. The `eval/` directory
stores post-hoc evaluator outputs; `score_report.json` and `metric_table.csv`
are not agent submissions.

`runs/<task_id>/<run_id>/` is the canonical layout for benchmark runners. The
current dry-run skeleton may still write to `runs/<run_id>/` with root-level
`artifacts/`, `scores.json`, and `summary.csv`; that simplified layout is only
a contract smoke test and should not define the final runner layout.
Tests for this layout should be treated as smoke-test compatibility checks, not
as acceptance tests for the final benchmark run directory.

The `input/` directory contains only agent-visible material. It may contain the
task prompt, shared HypoTrace output skill, shared output template, and mounted
data. The shared output controls are sourced from `contracts/HYPO_TRACE_SKILL.md`
and `contracts/output_template/`. It must not contain hidden references, scoring
rubrics, evaluator prompts, or curation-only reference chains.

## Hidden References

Task-specific hidden references may live under
`tasks/<task_id>/references/`, `references/<task_id>/`, or an equivalent
evaluator-only path. They may include truth files, hidden chokepoints, expert
curation notes, and grading assets. Agent input may only be copied from
agent-visible material in the task bundle, such as `input/`, visible data
mounts, or approved starter workspace files. Do not expose hidden references in
agent-facing prompts or starter workspaces.

Do not store raw datasets, reference answers, submissions, trajectories, or
grading outputs in the Git repository.

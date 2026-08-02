# Data Contract

The default data root is `/mnt/NAS_21T/ProjectData/HypoTrace_Data`.

Required subdirectories:

- `raw_data/`: canonical pre-task source-screening and tool/method curation
  packages, public-database source snapshots, normalized metadata inventories,
  article sources, later selected data objects, screen, source, case data, and
  case-derived chain artifacts.
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

## Public-Database Source Curation Layout

The STOmicsDB public-data route stores both source snapshots and normalized
curation records under `raw_data/public_database/stomicsdb/`; it does not use
`raw/public_database/stomicsdb/`.

`registry/intake_manifest.yaml:selected_stds_ids` is the ordered authority for
the active STOmicsDB storage, linkage, dispatch, and case-construction scope.
The dataset registry, paper registry, linkage edges, localization queue, and
acquisition plan must contain only entities owned by that allowlist. After an
approved hard scope reset, `registry/intake_generations/` contains only the
current frozen generation; superseded generation files and their staging state
are not retained. Nullable `parent_generation_id` and
`parent_manifest_sha256` fields identify such a reset without implying that a
parent generation remains available locally.

```text
/mnt/NAS_21T/ProjectData/HypoTrace_Data/
  raw_data/public_database/stomicsdb/
    registry/
      intake_manifest.yaml
      intake_generations/
        <generation_id>.yaml
      dataset_registry.jsonl
      paper_registry.jsonl
      linkage_edges.jsonl
      localization_queue.jsonl
      acquisition_plan.tsv
    staging/round1_article_dispatch/
      <dispatch_generation_id>/
        dispatch_state.yaml
        assignments/
          <paper_id>__attempt_<n>.yaml
        generations/
          <paper_id>/
            paper/
            datasets/
              <STDS_ID>/
    staging/round2b_bundle_validation/
      <dispatch_generation_id>/
        assignments/
        generations/
    auxiliary_resources/
      <package_id>/
        generations/
          <generation_id>/
            localization.yaml
            artifacts/
    datasets/<STDS_ID>/
      article/
        article.pdf
        article_manifest.yaml
      source/
      dataset_manifest.yaml
      source_manifest.yaml
      samples.jsonl
      files.jsonl
      resource_selection.yaml
      bundles/<bundle_id>/
        localization.yaml
        artifacts/
        extracted/
    papers/<paper_id>/
      source/
        article.pdf
      paper_manifest.yaml
      source_manifest.yaml
      linked_datasets.yaml
      resource_links.yaml
      resource_selection.yaml
      bundles/<bundle_id>/
        localization.yaml
        artifacts/
        extracted/
    cases/
      stomicsdb_<STDS_ID>/
        case_manifest.yaml
        source_manifest.yaml
        data/
          case_data_manifest.yaml
        dual_chain/  # downstream-owned after canonical case publication
```

Transient Round 1 dispatch state is stored under:

```text
raw_data/public_database/stomicsdb/staging/round1_article_dispatch/
  <dispatch_generation_id>/
    dispatch_state.yaml
    assignments/
      <paper_id>__attempt_<n>.yaml
    generations/
      <paper_id>/
        paper/
        datasets/
          <STDS_ID>/
```

`dispatch_state.yaml` records the frozen intake hash, dispatch generation,
canonical contract hashes, queue-row states, assignment hashes, attempt numbers,
worker-window identifiers, window status, runtime capacity observations, staged
generation IDs, and terminal publication results. It does not define a fixed
worker count or parallel-agent upper bound. Workers never write this file.

The dispatch state uses these closed values:

```yaml
queue_state: migration_required | not_started | running | staged | retryable | awaiting_human_review | complete | partial | failed
window_status: not_opened | active | close_required | closed
```

It also stores the exact frozen canonical contract hashes used for dispatch:

```yaml
contract_hashes:
  localization_workflow_sha256:
  data_contract_sha256:
  article_worker_protocol_sha256:
  single_worker_dispatch_sha256:
  batch_dispatch_sha256:
```

Dispatch preflight recomputes all five SHA-256 values and rejects any mismatch
before creating worker windows.

Round 2B bundle-validation staging uses:

```text
raw_data/public_database/stomicsdb/staging/round2b_bundle_validation/
  <dispatch_generation_id>/
    assignments/
      <bundle_id>__attempt_<n>.yaml
    generations/
      <bundle_id>/
```

### Round 1.5 File-Level Acquisition Plan Contract

`registry/acquisition_plan.tsv` is the only canonical input to the Round 2A background downloader. It contains exactly the header `source_url<TAB>target_path` and one row per physical transfer object.

`source_url` is a direct HTTP or HTTPS file URL. `target_path` is NAS-data-root-relative and resolves under the `artifacts/` directory of an approved bundle. Empty values, absolute target paths, `..` traversal, duplicate target paths, accessions, landing pages, repository roots, directory listings, and unresolved placeholders are invalid.

The TSV contains no status, bundle identifier, expected size, expected checksum, acquisition identifier, or separate revision column. Bundle membership is encoded by `target_path`; code revision is encoded by a commit-fixed archive URL.

A locator-only revision keeps the two-column contract unchanged. The
coordinator binds the old plan SHA-256, matches each exact existing
`target_path` and expected old `source_url`, replaces only `source_url`, and
validates the complete proposed plan before atomic publication. The transaction
receipt is NAS-resident and records the old and new plan hashes plus each old
and new sanitized locator. It must not contain credentials or change target
paths, queue rows, bundle IDs, resource references, ownership, or selected
representation. Any such change is a new resource-selection or scope revision,
not a locator override.

The downloader does not modify this file. Download progress remains operational state. `localization.yaml` is published only by the later post-download validation step and remains the sole canonical owner of bundle-level Round 2 terminal status.

`datasets/<STDS_ID>/` is the canonical owner for one STOmicsDB dataset entity.
Dataset packages own STOmicsDB metadata, STSP/STDF/accession records, and direct
STOmicsDB file locators. `source/` stores the latest validated dataset source
snapshot. `dataset_manifest.yaml` stores normalized dataset identity, source
status, linkage state, Round 1 `source_acquisition_status`, and applicable
`linkage_edge_id` references. `source_manifest.yaml` records source snapshot
provenance.
`samples.jsonl` stores normalized STSP/accession/sample records. `files.jsonl`
is the complete canonical inventory of normalized STDF/accession/file records
and direct STOmicsDB file locators. Automated resource selection selects queue
resources; it does not remove source records from `files.jsonl`. Dataset-owned
`bundles/<bundle_id>/` directories contain sample or shared data bundles. Each
directory owns its Round 2 `localization.yaml` and downloaded `artifacts/`.

`papers/<paper_id>/` is the canonical owner for one DOI-deduplicated article
entity. `paper_id` follows the public-data semantic contract:
`doi_sha256_<first 16 hex characters>` computed from the normalized DOI.
`source/` stores the latest validated article landing page, PDF, text, and
related accessible article source snapshots. `paper_manifest.yaml` stores
article identity, DOI normalization, source status, linkage state, and Round 1
`source_acquisition_status`. `source_manifest.yaml` records article-source
provenance.

`papers/<paper_id>/source/article.pdf` is the canonical DOI-deduplicated article
PDF. Each linked dataset contains an actual regular file at
`datasets/<STDS_ID>/article/article.pdf`. A symlink or pointer-only YAML file is
not sufficient.

The coordinator downloads and validates the PDF once, then materializes the
dataset-local file using a same-filesystem hard link when available, a reflink
when supported, or a byte-identical copy otherwise. Every materialized file must
have the same SHA-256 and size as the canonical paper PDF.

For a paper linked to multiple STDS records, every linked dataset receives its
own directly readable `article/article.pdf`; the network source is downloaded
only once.

The paper `source_manifest.yaml` owns the canonical PDF path and hash. Each
dataset's `article/article_manifest.yaml` owns the dataset-local PDF path, hash,
size, identity evidence, and materialization method. When no lawful anonymous or
operator-provided verified PDF is available, the article manifest records
`BLOCKED_EXTERNAL`; no `article.pdf` placeholder is created.
`operator_provided_verified_pdf` is an allowed article PDF acquisition status
only when an operator supplies the article PDF and the same publication checks
pass. The article manifest uses this contract:

```yaml
generation_id:
status: LOCALIZED | BLOCKED_EXTERNAL | IDENTITY_FAILED
paper_id:
source_doi:
article_title:
source_locator:
local_path: raw_data/public_database/stomicsdb/datasets/<STDS_ID>/article/article.pdf
canonical_paper_pdf: raw_data/public_database/stomicsdb/papers/<paper_id>/source/article.pdf
materialization: hardlink | reflink | copy
reported_size:
local_size:
sha256:
identity_evidence:
remaining_issue:
```

For `LOCALIZED`, `source_locator`, `local_path`, `canonical_paper_pdf`,
`materialization`, `local_size`, `sha256`, and `identity_evidence` are required;
`remaining_issue` is null. For `BLOCKED_EXTERNAL`, unavailable transfer fields
are null and `remaining_issue` records the exhausted lawful routes and external
condition. `IDENTITY_FAILED` is permitted only after coordinator-recorded human
adjudication confirms a terminal paper-identity conflict. Transfer and
materialization fields are null; `identity_evidence` and `remaining_issue` are
required. PDF completion is limited to the valid PDF signature, page count,
text extractability, DOI/title identity evidence, size, SHA-256, and
byte-identity of every linked-dataset materialization. The linked dataset still
requires an independently terminal Round 1A dataset manifest.

`linked_datasets.yaml` references the applicable `linkage_edge_id` values for
links to dataset-owned entities. Paper `resource_links.yaml` owns
article-derived data, code, supplement, repository, and project-page locators.
When these identify a dataset-owned object, the paper record references that
locator instead of copying it. `resource_links.yaml` records Round 1 locators;
it does not own Round 2 status. Paper-owned `bundles/<bundle_id>/` directories
contain code or auxiliary data bundles, with `localization.yaml` owning bundle
acquisition status and `artifacts/` containing transferred files. Every
resource-link record uses
these fields and closed values:

```yaml
kind: supplement | code_repository | code_archive | data_accession | data_file | project_page
locator_level: direct_file | accession | repository | landing_page
resolution_status: concrete | expandable | unresolved
access_status: declared_unchecked | resolved_public | restricted | unavailable
localization_status: not_requested
```

Entity manifests own Round 1 source-acquisition status only. They do not store
canonical Round 2 status. Each bundle's `localization.yaml` is the sole owner of
its Round 2 terminal state; any entity-level summary is derived and replaceable.

### Round 2B Bundle Localization Manifest Contract

Each approved bundle owns exactly one `localization.yaml` under:

```text
raw_data/public_database/stomicsdb/datasets/<STDS_ID>/bundles/<bundle_id>/localization.yaml
raw_data/public_database/stomicsdb/papers/<paper_id>/bundles/<bundle_id>/localization.yaml
```

Round 2B may also write necessary extracted content under the same bundle's
`extracted/` directory. It does not write outside the assigned bundle except for
transient staging records.

Archive inspection precedes extraction. Normalize the full member table and
reject absolute paths, `..` traversal, members resolving outside the assigned
`extracted/` root, normalized-path collisions, symbolic or hard links, and
device, FIFO, socket, or other special files. Only regular files and
directories may be materialized into a fresh per-attempt directory under the
assigned bundle. Every published extracted file records its source artifact,
path, SHA-256, and format. Existing extracted objects are never overwritten in
place, and an archive failing these checks cannot produce `LOCALIZED`.

The minimal `localization.yaml` contract is:

```yaml
generation_id:
round: "2B"
bundle:
  bundle_id:
  bundle_type:
  owner_type:
  owner_id:
  target_directory:
localization_status: LOCALIZED
assigned_conda_environment:
artifacts:
  - path:
    sha256:
    size_bytes:
    format:
    role:
extracted_paths:
  - path:
    source_artifact_path:
    sha256:
    format:
archive_members:
  - source_artifact_path:
    member_path:
    size_bytes:
basic_structure:
  h5_keys:
    -
  h5ad:
    dimensions:
    obs_columns:
      -
    var_columns:
      -
  coordinate_columns:
    -
  coordinate_ranges:
    -
  image_dimensions:
    -
  sample_identifiers:
    -
  metadata_columns:
    -
remaining_issue:
```

`expected_target_paths` is generated by the coordinator for the worker
assignment from the acquisition-plan rows whose `target_path` falls under the
approved bundle target prefix. Its entries remain NAS-data-root-relative and
are resolved against the assignment's absolute `nas_data_root`. It exists only
to verify that the expected physical files are present and complete; it is not
persisted in `localization.yaml` and is not a persistent `resource_ref` to
TSV-row coverage mapping.

`localization_status` values are `LOCALIZED | BLOCKED_EXTERNAL`. For
`LOCALIZED`, every expected target path is present, hash-recorded, and
structurally readable under the Round 2B boundary; `remaining_issue` is null.
For `BLOCKED_EXTERNAL`, `remaining_issue` records the unresolved external
condition and unavailable structural summaries may be empty. If the assigned
existing conda environment cannot read the format, the worker returns the
nonterminal `worker_status: awaiting_environment` and does not publish
`localization.yaml`; the coordinator retries with another already existing
environment. `BLOCKED_EXTERNAL` is reserved for conditions that truly require
external access, credentials, unavailable services, or unrecoverable remote
objects.

`assigned_conda_environment` records the assignment-specified existing host
conda environment or prefix used for format readers. Round 2B manifests must
not record package installation, environment creation, clustering, differential
expression, enrichment, spatial statistics, reannotation, format conversion,
biological interpretation, paper-result reproduction, case IDs, HVUs, or
`DATA_READY`.

### Post-Publication Revision And Cleanup Invariants

A correction to published selection, queue, plan, or localization metadata is
an allowlisted coordinator transaction. Its dry-run proposal records the exact
input paths and SHA-256 preconditions, the permitted field-level
transformations, the complete proposed output bytes and hashes, and downstream
generations made stale. Publication takes the relevant locks, rechecks every
precondition, validates the complete replacement set, preserves hashed backups,
and ends in recoverable `PREPARED`, `COMMITTED`, or `ROLLED_BACK` state. A
successful retry is idempotent. Presence of proposed bytes or a transaction
directory alone never implies commit.

A metadata repair cannot silently change scientific scope, resource identity,
bundle membership, target bytes, or representation. Those changes require the
applicable intake, resource-selection, or human scope revision contract. If a
dataset-local article or any referenced canonical data object changes, the
affected Round 3 case must be regenerated from the current bytes. Scientific
content is not amended in place. Regeneration publishes through this
post-publication transaction rather than first-publication rename, preserves
the prior case as recoverable transaction material, and marks every prior
dual-chain `input_binding` to the replaced three-manifest bytes stale. A stale
binding cannot remain `comparison_ready`; the chain must be regenerated or
reconfirmed against the new case binding.

An operator-authorized contraction of Round 3 auxiliary-resource scope is a
bounded scientific revision, not a metadata repair. The proposal binds the
source auxiliary inventory, the successful retained-resource acquisition
record, the exact case bytes, and the explicit retained and excluded resource
IDs. It may only remove existing content. For every excluded case-local `Axx`,
remove each directly linked `Rxx` and the transitive downstream closure of
explicit `result_connections`; then remove empty candidates and unreferenced
`Dxx` and `Axx` records. It must not add a result, alter a retained scientific
question or conclusion, infer a new connection, or reinterpret an execution
failure as scientific evidence. A case with surviving valid candidates remains
`accepted`; a case with none becomes `no_candidate` and has no canonical case
directory.

The transaction writes `revision_receipt.yaml` with the complete frozen-scope
status snapshot and `cleanup_receipt.yaml` with the superseded canonical paths,
file sizes, raw-byte SHA-256 values, recovery locations, and reference checks.
For current state resolution, a case entry in the newest successfully bound
`COMMITTED` revision receipt supersedes its historical Round 3 terminal without
modifying that terminal or its batch receipt. A `PREPARED` or `ROLLED_BACK`
transaction has no status authority. Current-version auxiliary downloads do
not by themselves turn formal Round 3 `Axx.local_availability: absent` into a
canonical local-data binding or `DATA_READY`; that requires a separately
contracted localization and downstream handoff.

Cleanup of candidate, staging, backup, or superseded bytes occurs only after a
NAS-resident cleanup receipt inventories each exact path, size, and SHA-256;
binds the committed replacement or terminal decision; verifies that no retained
manifest references the target; and records completion or failure per target.
Cleanup never treats a shared source object as exclusively owned and never
deletes canonical bytes merely because a candidate download completed.

### Round 3 Auxiliary Localization Ownership

Canonical auxiliary localization is separately owned from Round 2A download
staging and Round 2B STDS bundle localization. Its exact manifest field contract
is [the Round 3 auxiliary localization
template](../../contracts/output_template/stomicsdb/round3/auxiliary_localization.md).
An immutable generation is published only under:

```text
raw_data/public_database/stomicsdb/auxiliary_resources/
  <package_id>/generations/<generation_id>/
    localization.yaml
    artifacts/<filename>
```

There is no mutable `current` symlink or manifest. Paths below any `staging/`
directory, including completed Round 3 auxiliary download objects, are
acquisition evidence and never canonical case inputs. A canonical manifest
binds the package and generation IDs, resource identity and expected content,
source URL, immutable acquisition inventory and successful-run records,
`LOCALIZED` status, and every artifact's canonical path, source URL, format,
role, size, and raw-byte SHA-256. It also records the closed validation facts
defined by the template. It need not repeat access classification; the
case-local `Axx` preserves that scientific access evidence.

Package first-publication and binding into accepted cases are owned by one
recoverable `round3_auxiliary_localization_binding` transaction. They are
ordered phases, not separate transactions. Before canonical mutation, write
every complete package generation and every complete three-file case
replacement under unique NAS staging. Materialize package artifact bytes before
the manifest using a byte-stream copy or verified same-filesystem reflink; do
not use a metadata-preserving tree copy or hardlink to mutable download staging.
Serialize each package manifest last, then parse and validate all acquisition,
identity, containment, regular-file, readability, size, hash, and count
invariants. Validate every staged case replacement and retain hashed recoverable
backups and exact preconditions for every current case.

Acquire the complete package and case lock set and recheck every package
destination-absence and case-byte precondition. Under those locks, atomically
publish and reopen all package generations first. Only after every package is
canonically valid may any complete case tree be replaced. Only the selected
`Axx.local_availability` and its one localization binding may change. Resource
identity and access notes, all scientific `Rxx`, `Dxx`, and `Cxx` objects,
identifiers and references, and every other case field remain fixed; unchanged
source and case manifest bytes are identical. After all replacements validate,
mark every prior dual-chain input binding to replaced case bytes stale.
`COMMITTED` is permitted only when package publication, every case replacement,
and stale-chain handling all succeed and validate.

Any failure after package publication triggers compensation in the same
transaction. Restore every replaced case from its hashed backup, then delete
only package generations newly created by this transaction that no restored or
current case references. Reopen and validate the restored cases and verify that
no current case references a deleted generation before recording `ROLLED_BACK`.
Failure to prove restoration is not a valid terminal rollback. A failure before
canonical publication cleans only current-attempt staging. Download inventory,
run events, and source objects remain retained acquisition evidence in every
terminal state.

### Round 3 Case Output Ownership

Round 3 reads one dataset-local article package and the same STDS dataset's
canonical manifests and bundle objects. It does not use a discovery ledger,
auxiliary wave, per-edge state machine, or reviewer receipt.

The accepted case is exactly three files. `source_manifest.yaml` binds the
dataset-local article PDF and article manifest by path, raw-byte SHA-256, and
article generation ID. `case_data_manifest.yaml:dataset_binding` binds the
dataset manifest, dataset source manifest, `samples.jsonl`, and `files.jsonl` by
path and raw-byte SHA-256, including generation IDs for the two manifests. Each
logical `Dxx` binds every contributing `localization.yaml` by path, SHA-256, and
generation ID, and binds component files by path, format, and SHA-256. These are
upstream provenance hashes, not process hashes.

Accepted output is written only under:

```text
raw_data/public_database/stomicsdb/cases/stomicsdb_<STDS_ID>/
  source_manifest.yaml
  data/case_data_manifest.yaml
  case_manifest.yaml
```

The exact field contract is owned solely by
`contracts/output_template/stomicsdb/round3/case_outputs.md`.

The case directory references existing canonical dataset objects. It does not
copy article PDFs, raw data, bundle artifacts, extracted objects, or auxiliary
downloads.

Each `result_data_links[].data_inputs[]` identifies a `Dxx`, its scientific
input role, exact sample IDs, and required components with exact paths. Every
required component path is a subset of that referenced `Dxx` component's
`files[].path` values, and every sample ID resolves through the bound
`samples.jsonl`. Each `Dxx.data_context` contains exactly `organism`,
`tissue_or_context`, `spatial_assay`, `sample_summary`, and
`available_metadata`. There is no ambiguous top-level `Dxx.format`.

A formal auxiliary `Axx` is an identified required resource outside the STDS
package. It has `local_availability: absent | localized` and exactly one access
classification from `anonymous_direct | nonanonymous_access |
identified_not_directly_downloadable`. `absent` requires a null localization
binding and forbids package, artifact, hash, generation, and coverage fields.
`localized` preserves the same identity, expected content, source, access
classification, and notes and requires exactly one valid canonical package
binding. The binding selects a nonempty exact subset of package artifacts and
maps every expected-content requirement to selected artifact IDs with concise
structural evidence, `status: complete`, and no uncovered requirements.
`not_located` is valid temporary access evidence but makes an affected result
unsupported and is never persisted as an `Axx`. An `Axx` is never converted
into a `Dxx`.

For every candidate, each member result declares the same nonempty set of
`primary_spatial` `Dxx` inputs. `case_candidates[].spatial_data_ids` equals that
common set exactly. Main-article source support resolves through nonempty
`source_anchors` containing figure, table, or stable text locators.

All persisted local paths are NAS-data-root-relative. Raw data, candidate data,
temporary work, and execution output must not be written into the Git
repository.

A job with no supported candidate writes no case directory. A job with a review
or write failure has no accepted output. Existing case files are never
overwritten implicitly.

First publication uses an atomic case lock at:

```text
raw_data/public_database/stomicsdb/staging/round3_case_construction/locks/stomicsdb_<STDS_ID>.lock/
```

Lock creation is atomic and contention fails immediately. The lock records its
owner. A surviving lock is removed only after an operator confirms that owner
is abandoned. The worker writes the complete case tree under
`staging/round3_case_construction/<round3_batch_id>/<job_attempt_id>/stomicsdb_<STDS_ID>/`,
serializing the accepted objects directly into that NAS staging path. It does
not copy a complete tree from `/tmp` or another filesystem and does not use
`cp -a`, `rsync -a`, or another metadata-preserving tree copy. It parses and
compares all three objects, rechecks that the destination is absent, and
atomically renames the staged directory. It cleans only its current-attempt
staging. Existing cases require the post-publication transaction above.

The Round 3 coordinator owns durable batch records under:

```text
raw_data/public_database/stomicsdb/round3_runs/<batch_id>/assignment.yaml
raw_data/public_database/stomicsdb/round3_runs/<batch_id>/jobs/<STDS_ID>/started.yaml
raw_data/public_database/stomicsdb/round3_runs/<batch_id>/jobs/<STDS_ID>/terminal.yaml
raw_data/public_database/stomicsdb/round3_runs/<batch_id>/receipt.yaml
```

The bounded record shapes are:

```yaml
# assignment.yaml
round3_assignment:
  round3_batch_id:
  final_batch:
  repository_workdir:
  nas_data_root:
  contract_hashes:
    - {path:, sha256:}
  jobs:
    - {stds_id:, job_attempt_id:, dataset_directory:, case_directory:}

# jobs/<STDS_ID>/started.yaml
round3_job_started:
  round3_batch_id:
  job_attempt_id:
  stds_id:
  assignment: {path:, sha256:}
  dataset_directory:
  case_directory:

# jobs/<STDS_ID>/terminal.yaml
round3_job_terminal:
  round3_batch_id:
  job_attempt_id:
  stds_id:
  status: accepted | no_candidate | failed
  review_rounds:
  terminal_reason:
  reviewed_decisions: []
  final_issues: []
  output_paths: {source_manifest:, case_data_manifest:, case_manifest:}

# receipt.yaml
round3_receipt:
  round3_batch_id:
  assignment: {path:, sha256:}
  terminal_records:
    - {stds_id:, path:, sha256:, status:}
  counts: {accepted:, no_candidate:, failed:}
```

`assignment.yaml` is atomically written before any job work and contains the
fixed assignments and raw-byte hashes of the eleven normative Round 3 files
listed by the implementation-window contract. Each job uses the deterministic,
filesystem-safe `job_attempt_id` `<round3_batch_id>__<STDS_ID>`. `started.yaml`
is atomically written immediately before that job's preflight. `terminal.yaml`
is atomically written after closure with `accepted | no_candidate | failed`, terminal facts, concise
reviewed decisions, review count, and paths. `receipt.yaml` is written only
after every assigned job has a terminal record; it binds the assignment and
terminal hashes and reports counts. No start marker means `not_started`; start
without terminal means `interrupted`; a terminal marker is authoritative for
the recorded terminal status. These records exclude reasoning transcripts and
retry logs.

Failed legacy Round 3 staging remains incident evidence. It is not canonical
input, is not resumed, and is not interpreted as an accepted case.

### Public-Data Dual-Chain Handoff

One `case_candidates[].candidate_id` defines one downstream public-data chain
scope.

The consumer resolves:

- result content and analysis steps through `result_ids`;
- main-article evidence through each result's `source_anchors`;
- order through `result_order`;
- scientific continuity through `result_connections`;
- local inputs through `result_data_links[].data_inputs`, including
  `input_role`, `sample_ids`, and `required_components`;
- the common primary spatial set through `spatial_data_ids`;
- necessary external inputs through `auxiliary_resource_ids`;
- study framing through each referenced data object's `data_context`.

Candidate-eligible local data IDs are the union of `data_inputs[].data_id` for
the candidate's results. Every required component path must be hash-valid and a
subset of the referenced component files. Each member result has the same
nonempty `primary_spatial` set, and the candidate's `spatial_data_ids` equals
that set.

Round 3 candidate admission support and downstream execution availability are
separate decisions. Admission can retain an identified required `Axx` with
`local_availability: absent`; characterized external access alone never implies
`DATA_READY`. A selected candidate is execution-ready only when every required
local `Dxx` component path is readable and hash-valid and every required
auxiliary input is `localized` through a valid canonical package manifest,
artifact subset, and complete expected-content coverage record in the current
post-publication case generation. Until then, any required absent or invalid
`Axx` prevents `DATA_READY`. A URL, successful download, staging object, or
unbound canonical package is insufficient.

The consumer must use only the three case manifests and the article/data paths
they declare. It must not depend on legacy discovery files, audit responses,
worker history, or staging state.

### Round 1 Resource Selection Manifest Contract

After exact Round 1 closure for the effective intake manifest's declared paper,
dataset, and linkage-edge counts, the coordinator runs metadata-only automated
resource selection. It reads only `files.jsonl`, `resource_links.yaml`,
filenames, roles, sizes, access states, and locator metadata. It never opens
H5, H5AD, RDS, archive, image, or other resource objects; downloads resources;
inspects scientific results; or removes inventory rows.

Each dataset and paper owner publishes one `resource_selection.yaml` using this
contract:

```yaml
generation_id:
owner_type:
owner_id:
input_inventory_path:
input_inventory_sha256:
review_protocol_sha256:
status: AUTO_APPROVED | NEEDS_HUMAN_REVIEW | HUMAN_APPROVED
decisions:
  - resource_ref:
    action: retain | drop | review
    reason_code:
    proposed_bundle_type:
candidate_bundles:
remaining_issue:
```

`owner_type` is `dataset | paper`. Dataset manifests read
`files.jsonl`; paper manifests read `resource_links.yaml`. Every source
inventory record must receive exactly one decision in the matching selection
manifest. `retain` and `drop` are allowed only for deterministic metadata-level
classification. `review` is required for uncertain equivalence, processed/raw
ambiguity, shared ownership conflicts, or nonconcrete locators.

Automatic selection retains one clearly identified processed expression object
over an equivalent raw object; required coordinates, images, scalefactors,
metadata, platform support, reference inputs, and nonduplicated code resources;
and all resources needed for a complete proposed logical bundle. It drops clear
analysis outputs and demonstrably duplicate equivalents. It does not classify
scientific usability, case admission, sample-object linkage, article result
scope, or `DATA_READY`.

`status: AUTO_APPROVED` requires no `review` decisions and
`remaining_issue: null`. `status: NEEDS_HUMAN_REVIEW` requires at least one
`review` decision and a concrete `remaining_issue`. `status: HUMAN_APPROVED`
requires the human resolution to convert every source inventory record to one
final `retain` or `drop` decision. Only `AUTO_APPROVED` and `HUMAN_APPROVED`
manifests can contribute rows to `registry/localization_queue.jsonl`.

### Round 1 Entity Manifest Field Contract

The following field names are canonical for STOmicsDB Round 1 entity manifests.
Do not introduce aliases for them.

`dataset_manifest.yaml` requires:

```yaml
generation_id:
entity_type: dataset
stds_id:
official_landing_page_locator:
title:
species:
rating_evidence:
source_doi:
normalized_doi:
paper_id:
linkage_state:
linkage_edge_ids:
source_acquisition_status:
completion_receipts:
companion_records:
  # Must include article/article_manifest.yaml for every paper-linked dataset.
```

`paper_manifest.yaml` requires:

```yaml
generation_id:
entity_type: paper
paper_id:
source_doi:
normalized_doi:
citation_locator:
article_title:
linkage_state:
linkage_edge_ids:
source_acquisition_status:
completion_receipts:
companion_records:
```

`source_manifest.yaml` requires:

```yaml
generation_id:
entity_type:
entity_id:
retrieval_timestamp:
anonymous_access_status:
source_records:
  - path:
    source_locator:
    sha256:
    # role is optional.
```

Each source-record `path` is NAS-data-root-relative and must point to a
canonical published path, not a staging path. Source snapshots retain their
original bytes; encoding repair applies only to normalized metadata.
The paper source manifest owns the canonical `source/article.pdf` hash. The
dataset article manifest owns the dataset-local `article/article.pdf` hash, and
`dataset_manifest.yaml:companion_records` must include the
`article/article_manifest.yaml` canonical NAS-data-root-relative path and
SHA-256. Companion records must not publish staging paths. Successful canonical
publication requires deleting the corresponding staging generation unless it is
retained only for retry, human review, or a valid external-partial receipt.

A canonical package is current-generation terminal only when its required files,
fields, generation IDs, checksums, linkage coverage, and article materialization
satisfy the current contract. A legacy manifest marked `complete` but missing a
required canonical PDF, dataset-local article manifest, or current companion
record is `migration_required`, not terminal.

All local paths recorded in public-database manifests must be
NAS-data-root-relative unless explicitly marked as external URLs. YAML and JSONL
files must parse with standard parsers after writing. Each dataset, paper,
sample, file, linkage edge, and resource-link record must have one canonical
owner; other entities reference that owner instead of copying the record.

Refreshes retain only the latest validated snapshot. A refresh may replace
canonical files only after successful staging, parsing, and identity checks.

Future downloaded data remains dataset-owned. Paper and case packages reference
dataset-owned data objects rather than copying them.

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
For `case_route: public_database_stomicsdb`, it instead references the public
manifest's top-level `data_objects[].data_id`, restricted to IDs used by the
selected candidate results' `result_data_links[].data_inputs[].data_id` values.
Every member result declares the same nonempty set of `input_role:
primary_spatial` IDs, and candidate `spatial_data_ids` equals that common set.
Each required component path must be an exact path and hash match and a subset
of the referenced `Dxx` component files.

When a chain needs an internal package artifact, R object, CSV, RData object,
notebook output, or another object inside a localized top-level data object,
record it as an artifact reference under the parent data object instead of as
an independent top-level data object. Recommended shape:

```yaml
used_data_objects:
  - id: <case_data_manifest_data_object_id_or_public_data_id>
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

For `public_database_stomicsdb`, `used_data_objects[].id` is the Round 3
`data_id`; it is not an alias for a component path. The consumer reopens only
the selected results' declared article anchors and the referenced components
required by their analysis steps. Missing or contradictory candidate links,
logical roots, or required component paths are a Round 3 handoff
`needs_revision`; downstream extraction does not repair their scientific scope.

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

`runs/<task_id>/<run_id>/` is the canonical layout for benchmark runners.

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

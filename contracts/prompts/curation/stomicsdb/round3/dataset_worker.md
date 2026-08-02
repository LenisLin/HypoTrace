# STOmicsDB Round 3 Dataset Worker

## Purpose

Complete one Round 3 case-construction job for one dataset-local article and one
assigned STDS dataset. This worker is the sole evidence integrator, repair owner,
and formal case writer. Success depends on bounded source coverage, input
support, output-contract compliance, error handling, and traceability, not on a
favorable scientific result.

## Assignment

Receive one fully instantiated object:

```yaml
round3_job:
  round3_batch_id:
  job_attempt_id:
  stds_id:
  repository_workdir: /home/lenislin/Experiment/projects/HypoTrace
  nas_data_root: /mnt/NAS_21T/ProjectData/HypoTrace_Data
  dataset_directory:
  case_directory:
```

The paths must be exactly:

```text
dataset_directory:
  <nas_data_root>/raw_data/public_database/stomicsdb/datasets/<STDS_ID>
case_directory:
  <nas_data_root>/raw_data/public_database/stomicsdb/cases/stomicsdb_<STDS_ID>
```

`job_attempt_id` is the coordinator-assigned filesystem-safe identifier for this
single worker attempt. This worker owns only the assigned batch/job identity,
STDS ID, lock, current-attempt staging, and case destination.

## References

Read completely before scientific work:

- `AGENTS.md`
- `docs/datasets/stomicsdb-case-construction-workflow.md`
- `docs/datasets/public-data-research-case-extraction.md`
- `docs/datasets/data-contract.md`, limited to STOmicsDB source layout, Round 3
  ownership, and public-data dual-chain handoff
- `contracts/output_template/stomicsdb/round3/case_outputs.md`
- `contracts/prompts/curation/stomicsdb/round3/article_reader.md`
- `contracts/prompts/curation/stomicsdb/round3/resource_access_researcher.md`
- `contracts/prompts/curation/stomicsdb/round3/case_reviewer.md`

The output template is the sole accepted field contract. The standalone
checklist is read by the reviewer.

## Work

### Lock and manifest-driven preflight

1. Atomically create and record the current owner in:

   ```text
   <nas_data_root>/raw_data/public_database/stomicsdb/staging/round3_case_construction/locks/stomicsdb_<STDS_ID>.lock/
   ```

   Record `round3_batch_id`, `job_attempt_id`, and `stds_id` as the lock owner.
   Lock contention closes the job immediately as `failed`. Remove only this
   attempt's live lock after normal terminal closure. Never remove a surviving
   lock owned by another attempt; only an operator may do so after confirming
   its recorded owner is abandoned.
2. Confirm that `stds_id`, `dataset_directory`, and `case_directory` identify
   the same STDS dataset. Require `case_directory.parent` to be exactly
   `<nas_data_root>/raw_data/public_database/stomicsdb/cases`. If that shared
   parent is absent, create only that directory with concurrency-safe,
   idempotent semantics, then revalidate it. Reject a symlink, a non-directory,
   or an unwritable parent as a preflight failure. Never create the final
   `case_directory` during this step.
3. Parse and bind these exact dataset-local files:

   ```text
   article/article_manifest.yaml
   article/article.pdf
   dataset_manifest.yaml
   source_manifest.yaml
   samples.jsonl
   files.jsonl
   bundles/*/localization.yaml
   ```

4. Confirm article identity and record the article PDF path and SHA-256, article
   manifest path and SHA-256, and article-manifest `generation_id`. Record each
   dataset binding's path, raw-byte SHA-256, and required `generation_id`.
5. Resolve bundle localization records from the canonical manifest binding and
   parse every required `localization.yaml`. For each record, require every
   `artifacts[].path` and every nonempty `extracted_paths[].path` to remain
   inside the assigned dataset, exist, and be readable. Record the localization
   path, SHA-256, and `generation_id` for later `Dxx.localization_bindings`.
   Directory names alone are not inputs or prerequisites.
6. Treat `localization_status: BLOCKED_EXTERNAL` as evidence, not automatic
   preflight failure. Its declared present paths must still pass the checks
   above; unavailable material is considered later for the affected result.
7. Treat a missing, unreadable, unparsable, hash-contradictory, or identity-
   contradictory required binding or declared present path as `failed`.
8. Confirm that the final `case_directory` is absent. Preserve any existing
   content; any occupied destination is `failed` with
   `terminal_reason: existing_output_conflict`.

### Read the article once

Start exactly one article-reader subagent with `fork_turns: none`. Its initial
message directly contains one complete `article_reading_assignment` with the
STDS ID, repository workdir, and both dataset-local article paths, identifies
the `article_reader.md` path, requires immediate execution, and requires return
of only `article_results`. Do not replace the object with an assignment-file or
temporary-file path, a short summary, or an instruction to read the assignment
from disk.

A reader execution failure or `status: failed` closes the job as `failed`. A
complete response is fixed evidence for the rest of the job. Preserve every
returned `Rxx`; retained IDs may be non-contiguous. Carry that structured
response forward exactly. Do not manually transcribe, summarize, reconstruct,
or silently correct fixed reader evidence when constructing a reviewer
assignment; any required new reader evidence belongs to a new job attempt.

### Build the review-only result decisions

For every fixed `Rxx`, create exactly one working record:

```yaml
result_decisions:
  - result_id:
    uses_assigned_spatial_data: yes | no | uncertain
    spatial_basis:
    required_inputs: []
    local_data_ids: []
    auxiliary_resource_requests: []
    input_support: supported | unsupported | not_evaluated
    support_basis:
    final_disposition: candidate_eligible | excluded
    exclusion_reason:
```

This record is review-only and is never persisted in the accepted three files.
Use `not_evaluated` when spatial use is `no` or cannot be established as `yes`.
`candidate_eligible` requires exactly `uses_assigned_spatial_data: yes` plus
`input_support: supported`; every other combination is `excluded` with a
specific reason.

Spatial use requires assigned spatial expression, coordinates, or paired
spatial representation as an analysis input. Spatial discussion, a separate
validation assay, or an image used without assigned spatial measurements does
not establish use.

### Inspect relevant canonical data

Inspect actual canonical objects needed by potentially eligible results with
structured readers. Consolidate inspection so each component is read only to
the depth needed for schema, representation, sample mapping, and support.

Use one `Dxx` per coherent logical dataset. Paired expression, coordinates,
image, and metadata share a `Dxx` when assay identity and sample coverage are
compatible. A separate reference dataset, assay, or scientifically distinct
input receives another `Dxx`. File or bundle boundaries do not mechanically
define `Dxx` boundaries.

For each working object record `data_id`, narrow canonical `path`, `role`, the
exact localization bindings, and this bounded context:

```yaml
data_context:
  organism:
  tissue_or_context:
  spatial_assay:
  sample_summary:
  available_metadata: []
```

Record each component as null or:

```yaml
files:
  - path:
    format:
    sha256:
summary:
```

There is no top-level `Dxx.format`. Every component file path is
NAS-data-root-relative, hash-verified, declared by a bound localization record,
and mapped to exact relevant sample IDs from the bound `samples.jsonl`.

Inspect file completeness, actual schema, sample identity, pairing, and
representation meaning. Filename similarity, linkage, dimensions, or
co-location are provenance leads, not representation equivalence. Use existing
processed or canonical scientific objects; do not reconstruct reads or perform
normalization, clustering, differential analysis, enrichment, model fitting,
or result reproduction.

### Identify auxiliary inputs and decide support

For every `Rxx` with spatial use `yes`, list all necessary analysis inputs. If
any are absent from inspected canonical data, construct one immutable
resource-access assignment containing the complete dataset request list. Do not
start a researcher when the list is empty.

Start attempt 1 as a new leaf subagent with `fork_turns: none` and the internal
task name `resource_access_<stds_id_lowercase>_attempt_1`. The initial message
directly contains the complete immutable `resource_access_assignment`, with all
requests inline, identifies the `resource_access_researcher.md` path, requires
immediate execution, and requires return of only `resource_access`. Do not
replace the object with an assignment-file or temporary-file path, a short
summary, or an instruction to read the assignment from disk. Retry only when
the attempt returns no valid response because its selected model is at
capacity. A retry always creates a new leaf subagent, uses the identical inline
immutable assignment, and uses the next unique attempt suffix; never reuse the
failed leaf or send it a follow-up task. Apply this fixed schedule serially:

```text
attempt 1: start immediately
attempt 2: wait 5 seconds after attempt 1 reports model capacity
attempt 3: wait 30 seconds after attempt 2 reports model capacity
attempt 4: wait 60 seconds after attempt 3 reports model capacity
```

Stop after the first schema-valid response and do not start later attempts. Do
not merge partial content across attempts. A valid response with
`status: failed`, an invalid response, or any execution failure other than
selected-model capacity closes the job immediately without this retry path. If
attempt 4 also reports model capacity, close the job as `failed` with
`terminal_reason` set exactly to
`resource_access_researcher_execution_failure_after_4_attempts: Selected model is at capacity`.

For a non-capacity failure, preserve the stable upstream cause in
`terminal_reason`: use `resource_access_researcher_execution_failure: <exact
execution error>` when no valid response is returned, or
`resource_access_researcher_failed: <failure_reason>` when a valid response has
`status: failed`. Never collapse either condition to a generic
`resource_access_failure`.

Apply resource evidence without converting insufficient evidence into
inaccessibility, non-direct access into irrelevance, or failure to locate into
unnecessariness. `not_located` remains valid temporary evidence, makes every
affected result `unsupported`, and is never assigned an `Axx`. A required
identified resource may become formal `Axx` only with one of:

```text
anonymous_direct
nonanonymous_access
identified_not_directly_downloadable
```

Every formal `Axx` has `local_availability: absent`. Round 3 support means the
local `Dxx` and identified `Axx` records specify all inputs required by the
article-supported analysis at the relevant representation and sample scope. It
does not mean the input is execution-ready, the result was reproduced, or the
reported direction is favorable.

For every supported result, draft one `result_data_links` entry with
`data_inputs`. Each input states its `Dxx`, `primary_spatial | reference |
other_required` role, exact sample IDs, and required components with exact
paths. Every required path must be a subset of that `Dxx` component's
`files[].path` values.

### Construct the proposal

Assign `C01`, `C02`, ... only after all result decisions are complete. A
one-result candidate contains one eligible result. Connect multiple results
only when they use the same nonempty set of primary-spatial `Dxx` values, have
compatible assay and sample scope, preserve scientific order, and an upstream
analysis output is an explicit downstream input. Reference or auxiliary inputs
may differ. Connections are explicit and acyclic.

For every candidate, each member result must declare the same set of
`data_inputs` with `input_role: primary_spatial`; set `spatial_data_ids` equal
to that common set exactly. Include only final-candidate `Rxx`, `Dxx`, `Axx`,
links, and candidates in formal drafts.

Build one review proposal:

```yaml
case_proposal:
  stds_id:
  proposed_status: accepted | no_candidate
  result_decisions: []
  draft_outputs:
    source_manifest:
    case_data_manifest:
    case_manifest:
```

Use `accepted` only when at least one candidate exists and all three drafts are
non-null. Populate the exact provenance, component, input-role, sample, and
hash fields from the output contract. Use `no_candidate` only when zero results
are `candidate_eligible`; all three drafts are null. Both statuses require
review. Process state and `result_decisions` stay outside formal manifests.

Before constructing the reviewer assignment, mechanically validate every
SHA-256 value in the proposal and supplied `inspected_data`: each is exactly 64
lowercase hexadecimal characters and equals the corresponding fixed upstream
or inspection evidence. This check applies to review-only evidence as well as
formal drafts. A malformed or mistyped working hash is repaired from the fixed
evidence before round 1; it is not delegated to the reviewer and never changes
resource identity or scientific support.

### Run at most two review rounds

Construct the round-1 `case_review_assignment` in memory, then start exactly one
reviewer with `fork_turns: none` and keep that context for the optional second
round. The initial subagent message must contain the fully instantiated
`case_review_assignment` object itself, including the full proposal, fixed
article-reader response, inspected-data evidence, optional resource-access
response, and the assigned checklist and output-contract paths. A local or NAS
path, an instruction to open a transient file, or another pointer is not a
reviewer assignment and must never be the sole initial payload. Worker-local
transient files may help construct or validate the object, but the reviewer
must not depend on them. Here, "contain" means that the initial message exposes
the actual readable assignment structure; a gzip, base64, archive, or other
encoded blob that the reviewer must decode is not an inline assignment. The
reviewer must not materialize or decode its assignment through `/tmp`. If the
complete object cannot be submitted, do not start an unassigned reviewer;
return `failed` with the exact assignment-transport error.

The reviewer reports defects only. It performs a bounded scan of Results
headings and main-article figure/table/text anchors to assess inventory coverage;
it does not add `Rxx`, re-extract the article, repair objects, or write files.
An empty issue list accepts either proposal status.

If round 1 finds an omitted in-scope reader result, treat the fixed reader
inventory as nonrepairable in this window and return `failed`; obtaining a new
reader inventory requires a new implementation window. For all other issues,
the worker alone applies every repair together. A repair may change the
proposal between `accepted` and `no_candidate` if the repaired decisions
require it.

Use `followup_task` on that same reviewer context for the one permitted round-2
turn, and put the fully instantiated `case_review_revision` object itself in
that triggering follow-up, including the revised proposal, repaired targets,
and changed targets. A non-triggering `send_message` does not start round 2 and
must not be counted as a review response. Do not replace the revision object
with a path or transient-file instruction, and do not create a new reviewer. A
more precise read may cover only an already referenced component required by a
finding. Round 2 reviews repaired targets and directly affected references. An
empty issue list accepts the proposal. Any remaining issue is `failed` with the
full round-2 issue list. There is no third round or automatic restart.

### Atomic first publication

For an issue-free `no_candidate`, write no case directory and return
`no_candidate`.

For an issue-free candidate-bearing proposal:

1. Reconfirm that the validated shared case parent remains a real, writable,
   non-symlink directory and that the final case destination is absent.
2. Create the current-attempt case tree at:

   ```text
   <nas_data_root>/raw_data/public_database/stomicsdb/staging/round3_case_construction/<round3_batch_id>/<job_attempt_id>/stomicsdb_<STDS_ID>/
   ```

   The coordinator-assigned batch and attempt identifiers make this path unique.
3. Create the `data/` child and serialize the three accepted in-memory objects
   directly to `source_manifest.yaml`, `data/case_data_manifest.yaml`, and
   `case_manifest.yaml` in that staged case tree. Do not first build a complete
   tree under `/tmp` or another filesystem and copy it into staging. In
   particular, do not use `cp -a`, `rsync -a`, archive extraction, or another
   metadata-preserving tree copy. File identity is established by the accepted
   objects and raw bytes, not by preserving source ownership, mode, timestamps,
   ACLs, or extended attributes.
4. Parse all three YAML files, compare their objects with the accepted in-memory
   drafts, and validate all path, hash, sample, component-subset, candidate, and
   cross-reference invariants.
5. Recheck that the final destination is absent, then atomically rename the
   staged case directory to the assigned `case_directory`.
6. Return `accepted` only after reopening the three final files and confirming
   parsed-object equality.

On any staging, write, parse, comparison, destination, rename, or final check
failure, clean only this attempt's staging and return `failed`. Never remove or
replace existing case content. Regeneration uses the data contract's
post-publication transaction and marks previous dual-chain bindings stale; it
is outside first publication.

## Return

Return exactly:

```yaml
round3_job_response:
  round3_batch_id:
  job_attempt_id:
  stds_id:
  status: accepted | no_candidate | failed
  review_rounds:
  output_paths:
    source_manifest:
    case_data_manifest:
    case_manifest:
  terminal_reason:
  final_issues: []
```

`accepted` requires one or two completed reviews, three absolute present paths,
and empty `final_issues`. `no_candidate` requires issue-free review, null output
paths, and an evidence-workflow reason. `failed` uses null output paths and
distinguishes lock contention, preflight, article-reader, resource-access,
nonrepairable reader inventory, reviewer execution, unresolved review, staging,
and publication failures. Resource-access failures preserve the exact stable
execution error or returned `failure_reason` as specified above. Only unresolved
completed review populates `final_issues`.

`review_rounds` counts valid reviewer responses: zero before review, one after
round 1, and two after round 2. An invalid helper response does not increment
it. Release this attempt's owned live lock after establishing the terminal
response; leave any unconfirmed surviving lock for operator adjudication.

## Fixed boundaries

The worker handles one STDS dataset, uses only the dataset-local article and
assigned canonical data, and owns every repair and case write. It does not
create a third review, download auxiliary inputs, store runtime data in Git,
create HVUs, extract dual chains, admit benchmark tasks, or evaluate results.

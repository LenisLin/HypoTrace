# STOmicsDB Round 3 Case Construction Workflow

## Purpose and authority

This document is the canonical executable workflow for Round 3 case
construction. The [Round 3 output template](../../contracts/output_template/stomicsdb/round3/case_outputs.md)
is the sole authority for accepted output fields. The [standalone case review
checklist](../../contracts/checklists/stomicsdb/round3/case_review.md) is the sole
authority for review checks and responses. The [public-data case
definition](public-data-research-case-extraction.md) owns candidate semantics,
and the [data contract](data-contract.md) owns storage and downstream handoff.
Later canonical localization of a retained `Axx` is owned by the [Round 3
auxiliary localization
template](../../contracts/output_template/stomicsdb/round3/auxiliary_localization.md)
and does not reopen the original scientific review.

Round 3 determines whether article-supported analyses explicitly use the
assigned STDS spatial data and whether inspected data provide their required
inputs. It does not reproduce results or prefer favorable findings.

## Fixed input and output

Each job contains `stds_id`, absolute `dataset_directory`, and absolute
`case_directory`. The dataset-local source binding is:

```text
<dataset_directory>/article/article.pdf
<dataset_directory>/article/article_manifest.yaml
<dataset_directory>/dataset_manifest.yaml
<dataset_directory>/source_manifest.yaml
<dataset_directory>/samples.jsonl
<dataset_directory>/files.jsonl
<dataset_directory>/bundles/*/localization.yaml
```

The worker parses every assigned bundle `localization.yaml`. Each declared
`artifacts[].path` and each nonempty `extracted_paths[].path` must resolve under
the assigned dataset, exist, and be readable. The manifest path, raw-byte
SHA-256, and `generation_id` become the relevant `Dxx.localization_bindings`.
No directory name is itself a preflight requirement. A terminal
`localization_status: BLOCKED_EXTERNAL` is evidence about unavailable material,
not an automatic preflight failure; the worker decides support per result from
the declared available objects and required components.

The dataset worker derives article identity from `article_manifest.yaml` and
uses only the paired dataset-local PDF. It does not substitute the global DOI
paper directory or another STDS package.

An accepted job writes exactly:

```text
<case_directory>/source_manifest.yaml
<case_directory>/data/case_data_manifest.yaml
<case_directory>/case_manifest.yaml
```

The three files are first published together after issue-free review. Existing
case content is never overwritten implicitly.
Every `Axx` in this first publication has `local_availability: absent` and a
null localization binding. Downloading or locating the resource is outside the
case-construction job.

Each dataset worker requires the shared canonical parent
`raw_data/public_database/stomicsdb/cases/`. If it is absent, the worker creates
only that parent with concurrency-safe, idempotent semantics before scientific
work and then verifies that it is a real, writable, non-symlink directory. The
worker never creates its final `case_directory` during preflight.

## Batch model

A normal implementation window receives four explicit jobs and processes those
four assigned datasets concurrently. The final window may receive one to four
jobs only when its assignment attests that every remaining Round 3 job is
included. This four-dataset batch shape is not a global dataset-worker limit.

The coordinator owns atomic, durable batch records under
`raw_data/public_database/stomicsdb/round3_runs/<batch_id>/`:

```text
assignment.yaml
jobs/<STDS_ID>/started.yaml
jobs/<STDS_ID>/terminal.yaml
receipt.yaml
```

At startup, the implementation window must atomically create a previously
absent batch directory as its exclusive ownership claim. A second coordinator
that encounters an existing directory returns `invalid_batch` without joining
or resuming it, writing records, or spawning workers, even when the existing
`assignment.yaml` is byte-identical or the batch appears recoverable. Partial
or interrupted state remains incident evidence; retry uses a new batch ID and
new job attempt IDs.

The owning coordinator writes `assignment.yaml` before any job work,
`started.yaml` immediately
before each job-specific preflight, and `terminal.yaml` after that job closes as
`accepted | no_candidate | failed`. It writes `receipt.yaml` only after every
assigned job has a terminal record. Absence of `started.yaml` means
`not_started`; a start marker without a terminal marker means `interrupted`.
Records contain only assignments, contract hashes, terminal facts, concise
reviewed decisions, counts, and paths. Reasoning transcripts and retry logs are
excluded. The assignment binds the eleven normative Round 3 files listed by the
implementation-window prompt. Each job receives the deterministic,
filesystem-safe `job_attempt_id` `<round3_batch_id>__<STDS_ID>`.

The implementation window validates assignments, opens one dataset worker for
each valid job with `fork_turns: none`, and collects one terminal response per
job. One job's failure does not stop the others. A closed job is not retried in
the same window; any retry is a new assignment in a new window.

## Assignment transport

Every newly spawned Round 3 role uses `fork_turns: none` and receives its
complete instantiated assignment directly in the initial subagent message. The
controller inlines the complete batch assignment for the implementation window;
the window inlines the complete `round3_job` for each dataset worker; and the
dataset worker inlines the complete `article_reading_assignment`, immutable
`resource_access_assignment`, or round-1 `case_review_assignment` for the
corresponding leaf. All resource-access requests and all round-1 proposal and
evidence objects travel inside those assignments. The optional same-context
review round 2 is triggered with `followup_task` on the original reviewer and
receives the complete `case_review_revision` directly in that follow-up. A
non-triggering `send_message` does not create a review round, and round 2 never
starts a new reviewer.

An NAS `assignment.yaml` is a durable batch binding, not child-task transport.
An assignment path, `/tmp` path, short description, or instruction to read a
file never replaces the inline object. The message names the applicable role
prompt, states that the task is immediately executable, and requires only that
role's schema-valid response. Inline transport exposes the actual readable
structured assignment; gzip, base64, archives, or other encoded blobs that a
child must decode are not assignments. Worker-local transient files may be
used to construct and validate an assignment, but no leaf may materialize,
decode, or read its assignment through `/tmp`. Fixed leaf responses are carried
forward exactly rather than manually transcribed or reconstructed. A role that
does not receive a recognizable complete assignment is an execution/transport
failure, never scientific evidence and never `no_candidate`.

## Role model

Round 3 has exactly five role prompts:

- [implementation window](../../contracts/prompts/curation/stomicsdb/round3/implementation_window.md):
  validates and distributes one bounded batch and owns its persistent records;
- [dataset worker](../../contracts/prompts/curation/stomicsdb/round3/dataset_worker.md):
  owns one STDS job, integrates evidence, repairs findings, and is the sole
  formal case writer;
- [article reader](../../contracts/prompts/curation/stomicsdb/round3/article_reader.md):
  reads one complete article and returns the fixed ordered Results inventory;
- [resource-access researcher](../../contracts/prompts/curation/stomicsdb/round3/resource_access_researcher.md):
  characterizes the complete set of specifically requested missing auxiliary
  inputs in one pass;
- [case reviewer](../../contracts/prompts/curation/stomicsdb/round3/case_reviewer.md):
  performs evidence-bounded review in one context for at most two rounds.

The article reader and resource-access researcher are leaf roles and write no
files. The case reviewer reports defects and writes no files. Canonical-data
inspection, evidence integration, every repair, and case publication remain
with the dataset worker.

## Dataset procedure

1. Validate STDS identity, dataset-local article and canonical-manifest
   bindings, parsed localization records, their declared readable paths, and
   absence of conflicting case output.
2. Read the complete article once through one article reader. Assign stable
   `Rxx` IDs in article order before filtering.
3. For every fixed `Rxx`, record the review-only spatial-use and input-support
   decision. Retain only results with `uses_assigned_spatial_data: yes` and
   `input_support: supported`.
4. Inspect each relevant logical scientific dataset once. Group paired
   expression, coordinates, image, and metadata under one logical `Dxx` when
   assay identity and sample coverage are compatible.
5. Request one aggregated access characterization only when a potentially
   eligible result needs a specific auxiliary input absent from inspected
   canonical data. The dataset worker starts one leaf attempt immediately. Only
   a selected-model-capacity execution failure is retryable: wait 5, 30, and 60
   seconds before up to three serial retries, creating a new leaf subagent with
   the identical fixed request list each time. Stop on the first schema-valid
   response; never reuse a failed leaf or merge partial responses. Capacity on
   all four attempts is a terminal execution failure. `not_located` remains
   temporary evidence, makes the affected result unsupported, and is never
   emitted as `Axx`.
6. Build independent or connected `Cxx` candidates. Every member result has the
   same nonempty primary-spatial `Dxx` set, and candidate `spatial_data_ids`
   equals that set. Connect results only when an upstream result output is an
   explicit downstream input.
7. Form a proposal with `proposed_status: accepted | no_candidate`, the complete
   review-only `result_decisions`, and either the exact three draft objects or
   null drafts. Route both proposal types through review.
8. Deliver the fully instantiated round-1 review assignment directly in the
   reviewer subagent message; a transient-file path or other pointer is not an
   assignment. Run the complete checklist in review round 1. The reviewer may
   perform only its bounded Results-heading/figure/table/text coverage scan; it
   reports omissions without adding or renumbering `Rxx`.
9. Apply all repairable findings together. Reader-inventory omissions cannot be
   repaired in the current window and close the job as `failed`; a new window
   is required. Other repairs may receive one same-context round-2 review.
10. After issue-free review, return `no_candidate` without a case directory or
    publish an accepted case through the atomic first-publication procedure.

Producing no candidate (`no_candidate`) is a valid scientific outcome and is
not an execution failure. Helper failure, nonrepairable reader omission,
unresolved review, lock contention, or publication failure returns `failed`.

## Review loop

Round 1 reviews both proposal types. Common checks cover bounded main-article
Results coverage, exactly one decision per fixed `Rxx`, evidence-supported
spatial-use and input-support decisions, closure from every eligible decision
to a candidate, and validity of a zero-eligible `no_candidate`. Formal
three-file checks apply only to a candidate-bearing proposal.

If round 1 reports repairable issues, the dataset worker repairs all of them in
one change. Round 2 checks only repaired targets and directly affected
references. Unchanged evidence and conclusions remain fixed. An empty round-2
issue list is acceptance; any remaining issue closes the job as unresolved.
There is no third round and no automatic job restart.

## Publication

Before job work, atomically acquire the case lock at:

```text
staging/round3_case_construction/locks/stomicsdb_<STDS_ID>.lock/
```

Record `round3_batch_id`, `job_attempt_id`, and `stds_id` as the lock owner.
Contention fails immediately. The owner removes its lock after normal terminal
closure. A surviving lock is removed only after an operator confirms that its
recorded owner is abandoned.

For an accepted proposal, write the complete three-file case tree under
`staging/round3_case_construction/<round3_batch_id>/<job_attempt_id>/stomicsdb_<STDS_ID>/`.
Serialize the accepted in-memory objects directly into that NAS staging tree;
do not copy a prepared tree from `/tmp` or another filesystem, and do not use
`cp -a`, `rsync -a`, or another metadata-preserving copy. Parse all three YAML
objects, compare them with the issue-free in-memory objects, validate their
cross-references, recheck that the shared case parent remains a real, writable,
non-symlink directory and that the final case destination is absent, and
atomically rename the staged case directory to the final destination. Clean
only the current attempt's staging. A failed or partial attempt never removes
or replaces an existing case.

Regeneration of an existing case uses the post-publication transaction defined
in the data contract. It preserves recoverable prior content and marks old
dual-chain input bindings stale; it never uses first-publication overwrite.

After Round 3 closure, an operator may explicitly exclude unresolved auxiliary
resources while retaining identified resources that have a successful bounded
acquisition record. Apply that decision only through the data-contract
post-publication scope-contraction transaction. The transformation is
deterministic deletion: remove results directly linked to excluded `Axx`
records, close the removal transitively over explicit downstream
`result_connections`, and remove records no longer referenced by a surviving
candidate. It does not repeat article inventory, add evidence, or renumber
surviving `Rxx`, `Axx`, or `Cxx` identifiers. The committed revision receipt is
the current-status authority; historical batch records remain immutable.

Operator-authorized auxiliary localization uses one recoverable
`round3_auxiliary_localization_binding` transaction for both canonical package
first-publication and complete case-tree replacement. The package is an
immutable generation below
`auxiliary_resources/<package_id>/generations/<generation_id>/`, never a
download staging path. Before canonical mutation, stage and validate every
package `localization.yaml` and artifact tree and every complete three-file case
replacement. The coordinator binds exact preconditions, retains hashed
recoverable case backups, takes the complete case and package lock set, and
rechecks all preconditions.

Under those locks, publish and reopen all package generations first. Only after
all packages validate may the same transaction replace cases. A replacement may
change only the selected `Axx.local_availability` from `absent` to `localized`
and its one localization binding. The binding names and hashes the immutable
package manifest, selects the exact nonempty artifact subset required by the
`Axx`, and records complete expected-content coverage with no uncovered
requirement. Resource identity and access evidence, scientific `Rxx`, `Dxx`,
and `Cxx`, identifiers, ordering, references, and all other case fields remain
fixed. The source and case manifest bytes remain identical.

After all replacements validate, mark prior dual-chain inputs bound to replaced
case bytes stale. `COMMITTED` is valid only after package publication, every
case replacement, and stale-chain handling all succeed. Any later failure
restores every replaced case from its hashed backup and deletes only package
generations created by this transaction that no restored or current case
references. Validate the restored cases and absence of current references to
deleted generations before recording `ROLLED_BACK`. Package publication and
case adoption are not separate transactions.

This transaction changes availability evidence, not the case's scientific
admission. `DATA_READY` is derived only after every referenced `Dxx` and every
localized `Axx` package, artifact subset, and expected-content coverage binding
validates. A source URL, download terminal, staging file, or unbound canonical
package is insufficient.

## Terminal response

Each dataset worker returns exactly one in-memory response:

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

`accepted` requires issue-free review, atomic publication of the three output
paths, successful YAML parsing, and parsed-object equality. `no_candidate` and
`failed` return null output paths. Only an unresolved completed review populates
`final_issues`. `review_rounds` counts completed reviewer responses from zero to
two; an execution attempt without a valid response does not increment it.
For a resource-access execution failure or a valid researcher response with
`status: failed`, `terminal_reason` preserves the exact stable execution error
or returned `failure_reason`; a generic `resource_access_failure` is invalid.

## Scientific and engineering boundaries

Round 3 records article-supported questions, conclusions, and analysis steps;
it does not assert that conclusions are true, causal, replicated, or favorable.
Portal linkage and dataset-local article presence establish provenance, not
analysis-input support. Candidate admission and downstream execution
availability are separate decisions.

Round 3 does not execute scientific analyses, reconstruct read-level data,
download auxiliary resources, create downstream HVUs, or write raw or runtime
data into Git. Formal local paths are NAS-data-root-relative, references resolve
within the assigned STDS package, credentials remain outside prompts and
returns, and process state remains outside accepted output.

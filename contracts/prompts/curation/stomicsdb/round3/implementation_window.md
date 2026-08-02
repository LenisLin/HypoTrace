# STOmicsDB Round 3 Implementation Window

## Purpose

Coordinate one bounded batch of dataset-scoped Round 3 jobs. Each dataset
worker owns the scientific work and formal case output for one assigned STDS
dataset. The implementation window owns assignment validation, bounded
distribution, atomic batch records, and terminal response collection.

## Assignment

Provide one fully instantiated YAML object:

```yaml
round3_batch_id:
repository_workdir: /home/lenislin/Experiment/projects/HypoTrace
nas_data_root: /mnt/NAS_21T/ProjectData/HypoTrace_Data
final_batch: false
jobs:
  - stds_id:
    dataset_directory:
    case_directory:
```

The controller starts this implementation window with `fork_turns: none`. The
initial subagent message itself contains the complete instantiated batch object
above and identifies this prompt path. An `assignment.yaml` path, temporary-file
path, or instruction to read an object from disk is not task transport and must
not replace the inline batch object. `assignment.yaml` is the durable binding
written by the implementation window after validating the inline assignment.

A normal batch has exactly four jobs and `final_batch: false`. The last batch
may contain one to four jobs and uses `final_batch: true`; this attests that the
assignment contains every remaining Round 3 job.

Each job uses:

```text
dataset_directory:
  <nas_data_root>/raw_data/public_database/stomicsdb/datasets/<STDS_ID>

case_directory:
  <nas_data_root>/raw_data/public_database/stomicsdb/cases/stomicsdb_<STDS_ID>
```

Require a nonempty filesystem-safe batch ID without path separators or `..`,
unique STDS IDs, unique case directories, absolute paths, matching path
identities, and no unresolved placeholders. A malformed batch is rejected
before persistent assignment publication or job work.

## References

Read only:

- `AGENTS.md`
- `docs/datasets/stomicsdb-case-construction-workflow.md`, limited to the
  authority, fixed input/output, batch model, publication, and terminal-response
  sections
- `contracts/prompts/curation/stomicsdb/round3/dataset_worker.md`

Compute raw-byte SHA-256 values for the normative files actually used by this
batch and record their paths and hashes in the assignment:

- `AGENTS.md`
- `docs/datasets/stomicsdb-case-construction-workflow.md`
- `docs/datasets/public-data-research-case-extraction.md`
- `docs/datasets/data-contract.md`
- `contracts/output_template/stomicsdb/round3/case_outputs.md`
- `contracts/checklists/stomicsdb/round3/case_review.md`
- this implementation-window prompt
- `contracts/prompts/curation/stomicsdb/round3/dataset_worker.md`
- `contracts/prompts/curation/stomicsdb/round3/article_reader.md`
- `contracts/prompts/curation/stomicsdb/round3/resource_access_researcher.md`
- `contracts/prompts/curation/stomicsdb/round3/case_reviewer.md`

## Coordinator Records

After validating the whole assignment and before any job work, atomically create
the batch directory as this implementation window's exclusive ownership claim,
then atomically write:

```text
<nas_data_root>/raw_data/public_database/stomicsdb/round3_runs/<batch_id>/assignment.yaml
```

The batch directory must not exist when this implementation window starts. If
the exclusive directory creation reports that it already exists, return
`invalid_batch` immediately without reading an existing assignment as a reason
to join or resume that batch, without writing any record, and without spawning
any dataset worker. An identical existing `assignment.yaml`, an empty jobs
directory, or apparently recoverable partial state does not transfer ownership
to a second coordinator. Preserve that directory as incident evidence; the
controller decides any retry through a new batch ID and new job attempt IDs.

It contains the batch assignment and contract paths plus hashes. Before each
job-specific preflight, atomically write:

```text
round3_runs/<batch_id>/jobs/<STDS_ID>/started.yaml
```

After that job closes, atomically write `terminal.yaml` beside its start marker.
The terminal record contains the assigned identity, `accepted | no_candidate |
failed`, review-round count, concise terminal reason, concise final reviewed
issues when applicable, and output paths. Preserve the worker response facts;
do not add a reasoning transcript.

Only after every assigned job has a valid terminal record, atomically write:

```text
round3_runs/<batch_id>/receipt.yaml
```

The receipt contains the batch ID, assignment path and hash, terminal-record
paths and hashes, and accepted/no-candidate/failed counts. It excludes worker
messages, retry logs, and reasoning history. The records make recovery
unambiguous: no start marker means `not_started`; a start marker without a
terminal marker means `interrupted`; a terminal marker records the actual
terminal status. Never infer a terminal state from a missing response or write
the receipt early.

Use exactly these bounded objects:

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

`reviewed_decisions` is a concise terminal summary, such as proposal status and
eligible-result count. It is not the full review-only `result_decisions`
evidence record.

## Work

1. Validate the batch object and its normal or final batch size. Derive each
   filesystem-safe `job_attempt_id` as `<round3_batch_id>__<STDS_ID>`.
2. Compute the required contract hashes, atomically claim a previously absent
   batch directory, and atomically publish the assignment, including every
   derived `job_attempt_id`, before starting any job. If the batch directory
   already exists, return `invalid_batch` immediately; never recover, resume,
   or join it from a newly spawned implementation window.
3. For each assigned job, atomically publish `started.yaml` immediately before
   job-specific preflight.
4. Validate that job's path identity, required dataset directory, dataset-local
   article package, canonical manifests, and absence of a conflicting case
   destination. Record a terminal `failed` result for a preflight failure; other
   jobs continue.
5. Start exactly one dataset-worker subagent for every valid job and dispatch
   all valid jobs in the four-dataset batch concurrently, with
   `fork_turns: none`. Do not impose a separate dataset-worker upper bound.
6. Make each dataset-worker initial message directly state that it is an
   immediately executable Round 3 dataset-worker job, require direct execution
   and return of only `round3_job_response`, identify the `dataset_worker.md`
   path, and inline one complete instantiated `round3_job` object. That object
   includes `round3_batch_id`, `job_attempt_id`, `stds_id`,
   `repository_workdir`, `nas_data_root`, `dataset_directory`, and
   `case_directory`. A durable assignment path, temporary-file path, short
   summary, or instruction to read an assignment from disk is not child-task
   transport and must not replace any of these inline fields.
7. Keep one worker attempt per job in this implementation window. A worker
   response, execution failure, or invalid response closes that job. A retry is
   a new assignment in a new implementation window.
8. Collect exactly one terminal response for every started job and atomically
   publish the corresponding `terminal.yaml` after closure.
9. For `accepted`, confirm mechanically that the three returned output paths
   exist at the assigned case directory. Scientific content remains the dataset
   worker and case reviewer's responsibility.
10. Continue collecting other jobs when any one job returns `accepted`,
    `no_candidate`, or `failed`.
11. Reopen every terminal record, compute its hash, and atomically publish
    `receipt.yaml` only when all assigned jobs have terminal records.
12. Return the batch response matching the durable terminal records.

The implementation window starts dataset workers only. Literature reading,
resource-access research, and case review are delegated by each dataset worker
inside its isolated context. The assignment defines one concurrent round of four
datasets; it does not define a global dataset-worker limit.

## Return

Return:

```yaml
round3_batch_response:
  round3_batch_id:
  status: complete | invalid_batch
  assignment_path:
  receipt_path:
  jobs:
    - stds_id:
      job_attempt_id:
      status: accepted | no_candidate | failed
      review_rounds:
      output_paths:
        source_manifest:
        case_data_manifest:
        case_manifest:
      terminal_reason:
      final_issues: []
      started_path:
      terminal_path:
  counts:
    accepted:
    no_candidate:
    failed:
  invalid_batch_reason:
```

Each worker response must repeat the assigned `round3_batch_id` and
`job_attempt_id`; a mismatch is an invalid response and closes that job as
`failed`. For `accepted`, all three output paths are absolute and present. For
`no_candidate` and `failed`, all three values are null. `review_rounds` is the
worker-reported completed-review count; an immediate coordinator failure uses
zero. Preserve a resource-access failure's exact stable execution error or
returned researcher `failure_reason` in `terminal_reason`; do not normalize it
to a generic category. `invalid_batch` writes no batch records because no job
is authorized to start.

## Fixed boundaries

The implementation window creates no article interpretation, data
representation judgment, candidate, or review finding. It writes only the
coordinator-owned atomic batch records above; these records are operational
metadata, not accepted case output. They contain assignments, contract hashes,
terminal facts, concise reviewed decisions, counts, and paths only. It writes no
Git content, raw dataset, reasoning transcript, or retry log.

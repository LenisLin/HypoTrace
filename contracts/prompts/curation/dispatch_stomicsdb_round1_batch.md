# Dispatch: STOmicsDB Round 1 Article Batch

This is the coordinator wrapper for persistent scheduling of the effective
STOmicsDB Round 1 queue. It is not the article worker protocol.

## Required Batch Input

Provide a fully instantiated YAML object:

```yaml
effective_intake_generation_id:
effective_intake_sha256:
parent_intake_sha256:
dispatch_generation_id:
worker_capacity_policy: use_all_available
contract_hashes:
  localization_workflow_sha256:
  data_contract_sha256:
  article_worker_protocol_sha256:
  single_worker_dispatch_sha256:
  batch_dispatch_sha256:
expected_paper_count: <from effective intake deduplicated_paper_count>
expected_dataset_count: <from effective intake selected_stds_count>
expected_linkage_edge_count: <from effective intake linkage_edge_count>
queue_rows:
```

The expected counts are supplied by the effective intake manifest and must not
be replaced with historical initial-intake constants.

Each queue row supplies the complete single-worker assignment required by
`dispatch_stomicsdb_round1_article_worker.md` plus its reconciled queue state.
Reject duplicate paper IDs, duplicate or overlapping staging paths, canonical
path collisions, unresolved placeholders, relative filesystem paths, or an
effective intake hash that differs from the canonical workflow.

## Required References

Read and follow:

- `docs/datasets/data-contract.md`
- `docs/datasets/stomicsdb-localization-workflow.md`
- `docs/datasets/public-data-research-case-extraction.md`
- `contracts/prompts/curation/stomicsdb_round1_article_localization.md`
- `contracts/prompts/curation/dispatch_stomicsdb_round1_article_worker.md`

Recompute the five required canonical hashes before dispatch:

- `docs/datasets/stomicsdb-localization-workflow.md`
- `docs/datasets/data-contract.md`
- `contracts/prompts/curation/stomicsdb_round1_article_localization.md`
- `contracts/prompts/curation/dispatch_stomicsdb_round1_article_worker.md`
- `contracts/prompts/curation/dispatch_stomicsdb_round1_batch.md`

Reject the batch before creating worker windows if any recomputed value differs
from `contract_hashes`. Hash the instantiated single-worker prompt for each
assignment. Record the canonical hashes and assignment hashes in
coordinator-owned dispatch state so a resumed row cannot silently change
protocol or inputs.

## Persistent Scheduler Contract

Before dispatching any `not_started` paper, reconcile every existing canonical
package whose STDS ID appears in the current intake manifest's ordered
`selected_stds_ids` allowlist. Missing canonical PDFs, dataset-local PDFs,
article manifests, current companion records, or matching checksums force
`migration_required`. Derive the pending paper set from the current registries
and terminal state. Do not migrate or dispatch any STDS ID outside the frozen
allowlist.

At preflight and after every confirmed worker-window closure, rediscover
available worker capacity. Dispatch as many unique actionable assignments as
capacity permits. Do not fail preflight solely because a preferred worker count
is unavailable, and do not impose a fixed upper bound below the environment's
available capacity.

1. Verify that at least one article-worker window is available before dispatch.
   If no worker window is available, pause dispatch with a capacity observation
   and dispatch none.
2. Reconcile every queue row to one of the data contract's closed `queue_state`
   values using filesystem state, manifests, generation IDs, hashes, linkage
   coverage, and current-generation validity. A valid `partial` is terminal only
   when its blocker is externally caused and all lawful PDF routes were
   exhausted.
3. Pre-create unique absolute staging directories and instantiate the
   single-worker wrapper without placeholders for every dispatched paper.
4. Keep every available article-worker window occupied while actionable papers
   remain, subject to assignment uniqueness, publication safety, per-host
   network throttling, and external rate limits. When available capacity exceeds
   actionable papers, dispatch every remaining actionable paper without
   inventing work.
5. For every returned assignment, persist its assignment identity, staged paths,
   generation ID, status, and validation receipts in transient dispatch state.
   Mark its window `close_required`.
6. Close the completed subagent window and confirm that it is no longer active
   and its capacity has been released.
7. Validate and publish the staged generation, place it in human review, or
   requeue it as retryable. Update dispatch state with the result.
8. Open a replacement worker window only after the previous window is confirmed
   closed and actionable work and worker capacity remain. Requeue local failures
   without changing queue state to terminal or reducing available worker
   capacity while actionable work remains. Enforce per-host HTTP concurrency
   independently of worker capacity.
9. Before publication, validate PDF signature, page count, text extraction,
   bibliographic identity, schema, generation consistency, checksums, linkage
   coverage, regular-file status, and byte identity of all dataset copies.
10. The coordinator alone writes registries and canonical packages. Publish
    companion files first and atomically publish the manifest last while holding
    the applicable lock.
11. After successful publication, clean superseded staging and obsolete
    source-only or browser-wrapper staging for that entity. Preserve staging
    needed for retry, human review, or evidence of a valid external partial.
12. Continue until every paper, dataset, and effective-intake linkage edge has exact
    current-generation terminal accounting. Do not return an interim batch
    summary while actionable work remains.
13. Never start Round 2 automatically.

A returned worker window is never reused. Record its response, close the window,
confirm capacity release, validate the staged generation, update dispatch state,
and only then open a replacement window. Retryable work is dispatched in a new
window with an incremented attempt number.

## Completion Accounting

Completion requires terminal paper rows, dataset rows, and linkage-edge
coverage matching the effective intake manifest's declared counts. Counts must
contain no duplicate, missing, `migration_required`, `running`, `staged`,
`retryable`, or `awaiting_human_review` row. Every terminal row must satisfy
the current-generation contract. Round 2 remains unstarted.

The terminal response records the effective intake generation and hash,
dispatch generation, paper and dataset counts by terminal status, linkage-edge
coverage, and one remaining issue or identity-adjudication reason per
non-complete entity. Report canonical protocol and assignment hashes,
duplicate-path rejection results, capacity observations, publication validation
results, confirmed window closures, and cleanup completion. Do not create a
separate audit artifact.

Report observed capacity rather than a target:

```yaml
capacity_observations:
- observed_at:
  available_worker_windows:
  active_worker_windows:
  actionable_rows:
```

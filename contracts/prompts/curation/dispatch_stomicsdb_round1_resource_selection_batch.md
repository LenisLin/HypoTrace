# Dispatch: STOmicsDB Round 1 Resource Selection Batch

This is the coordinator wrapper for persistent scheduling of metadata-only
resource selection after effective-intake STOmicsDB Round 1 closure. It is not the
single-owner selection protocol.

## Required Batch Input

Provide a fully instantiated YAML object:

```yaml
effective_intake_generation_id:
effective_intake_sha256:
parent_intake_sha256:
selection_dispatch_generation_id:
worker_capacity_policy: use_all_available
contract_hashes:
  localization_workflow_sha256:
  data_contract_sha256:
  resource_selection_protocol_sha256:
  single_worker_dispatch_sha256:
  acquisition_plan_protocol_sha256:
  batch_dispatch_sha256:
expected_paper_selection_count: <from effective intake deduplicated_paper_count>
expected_dataset_selection_count: <from effective intake selected_stds_count>
expected_linkage_edge_count: <from effective intake linkage_edge_count>
owner_rows:
```

The expected counts are supplied by the effective intake manifest and must not
be replaced with historical initial-intake constants.

Each owner row supplies the complete single-worker assignment required by
`dispatch_stomicsdb_round1_resource_selection_worker.md` plus its reconciled
selection state. Reject duplicate owners, duplicate or overlapping staging
paths, canonical path collisions, unresolved placeholders, relative filesystem
paths where absolutes are required, missing inventories, or an effective intake
hash that differs from the canonical workflow.

## Required References

Read and follow:

- `docs/datasets/data-contract.md`
- `docs/datasets/stomicsdb-localization-workflow.md`
- `contracts/prompts/curation/stomicsdb_round1_resource_selection.md`
- `contracts/prompts/curation/dispatch_stomicsdb_round1_resource_selection_worker.md`
- `contracts/prompts/curation/stomicsdb_round15_acquisition_plan.md`

Recompute the six required canonical hashes before dispatch:

- `docs/datasets/stomicsdb-localization-workflow.md`
- `docs/datasets/data-contract.md`
- `contracts/prompts/curation/stomicsdb_round1_resource_selection.md`
- `contracts/prompts/curation/dispatch_stomicsdb_round1_resource_selection_worker.md`
- `contracts/prompts/curation/stomicsdb_round15_acquisition_plan.md`
- `contracts/prompts/curation/dispatch_stomicsdb_round1_resource_selection_batch.md`

Reject the batch before creating worker windows if any recomputed value differs
from `contract_hashes`. Hash each instantiated single-worker assignment and
record the canonical hashes and assignment hashes in coordinator-owned dispatch
state.

## Persistent Scheduler Contract

1. Start only after exact current-generation Round 1 closure matching the
   effective intake manifest's declared paper, dataset, and linkage-edge
   counts, and no `migration_required`, `running`, `staged`, `retryable`, or
   `awaiting_human_review` article-localization row.
2. At preflight and after every confirmed worker-window closure, rediscover
   available worker capacity. Dispatch as many unique actionable assignments as
   capacity permits. Do not fail preflight solely because a preferred worker
   count is unavailable, and do not impose a fixed upper bound below the
   environment's available capacity. If no selection-worker window is available,
   pause dispatch with a capacity observation and dispatch none.
3. Reconcile every owner row to `not_started`, `running`, `staged`,
   `retryable`, `needs_human_review`, `auto_approved`, or `human_approved` using
   filesystem state, manifests, generation IDs, inventory hashes, protocol
   hashes, and decision coverage.
4. Pre-create unique absolute staging directories and instantiate the
   single-worker wrapper without placeholders for every dispatched owner.
5. Keep every available selection-worker window occupied while actionable owners
   remain, subject to assignment uniqueness, publication safety, and external
   rate limits. When available capacity exceeds actionable owners, dispatch
   every remaining actionable owner without inventing work.
6. For every returned assignment, persist its assignment identity, staged path,
   generation ID, status, decision counts, and validation receipts in transient
   dispatch state. Mark its window `close_required`.
7. Close the completed subagent window and confirm that it is no longer active
   and its capacity has been released.
8. Validate and publish the staged `resource_selection.yaml`, place it in human
   review, or requeue it as retryable. Update dispatch state with the result.
9. Open a replacement worker window only after the previous window is confirmed
   closed and actionable work and worker capacity remain. Requeue local failures
   without changing queue state to terminal or reducing available worker
   capacity while actionable work remains.
10. Before publication, validate YAML parsing, owner identity, inventory
    SHA-256, protocol SHA-256, one-to-one decision coverage, candidate-bundle
    consistency, and absence of retained resources outside validated bundles.
11. The coordinator alone writes registry files and canonical owner packages.
    Publish the selection manifest atomically after validation.
12. Escalate ambiguous rows to human review without blocking unrelated
    selection work. Publish queue rows for ambiguous owners only after human
    resolution produces `HUMAN_APPROVED`.
13. Publish `registry/localization_queue.jsonl` only after every retained
    resource belongs to a validated logical bundle, every source inventory row
    has exactly one decision, and no unresolved review row remains.
14. After publishing the validated `registry/localization_queue.jsonl`, follow
    `contracts/prompts/curation/stomicsdb_round15_acquisition_plan.md` to publish
    the single canonical `registry/acquisition_plan.tsv`. Do not start download
    work. Treat approved-resource coverage as a pre-publication validation gate:
    retain the `resource_ref`-to-row mapping only while materializing and
    validating the TSV, then discard it. Do not add TSV columns, sidecar
    mappings, coverage reports, or audit artifacts.
15. Never download resources, inspect object contents, create case IDs, create
    `DATA_READY` records, write HVUs or dual chains, create Round 2 manifests,
    or start Round 2.

A returned worker window is never reused. Record its response, close the window,
confirm capacity release, validate the staged generation, update dispatch state,
and only then open a replacement window. Retryable work is dispatched in a new
window with an incremented attempt number.

## Completion Accounting

Selection-batch completion requires dataset and paper selection-manifest counts
matching the effective intake manifest, complete inventory decisions, no
unresolved review row, a validated approved bundle queue, and a complete
two-column acquisition plan.

The terminal response records the effective intake generation and hash,
dispatch generation, canonical contract hashes, capacity observations,
confirmed window closures, selection-manifest counts, decision counts by action
and reason code, approved bundle counts by bundle type and approval basis,
unresolved issues, duplicate path rejection results, publication validation
results, and cleanup completion. Do not create a separate audit artifact and do
not start Round 2.

Report observed capacity rather than a target:

```yaml
capacity_observations:
- observed_at:
  available_worker_windows:
  active_worker_windows:
  actionable_rows:
```

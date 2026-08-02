# Dispatch: STOmicsDB Round 2B Bundle Batch

This is the coordinator wrapper for Round 2B bundle validation. It is not the
bundle validation protocol.

## Required Batch Input

Provide a fully instantiated YAML object:

```yaml
effective_intake_generation_id:
effective_intake_sha256:
parent_intake_sha256:
dispatch_generation_id:
round2a_completion_evidence:
contract_hashes:
  localization_workflow_sha256:
  data_contract_sha256:
  bundle_worker_protocol_sha256:
  single_worker_dispatch_sha256:
  batch_dispatch_sha256:
queue_rows:
```

Each queue row supplies the complete single-bundle assignment required by
`dispatch_stomicsdb_round2b_bundle_worker.md` plus its reconciled queue state.
Reject duplicate bundle IDs, duplicate or overlapping staging paths, canonical
path collisions, unresolved placeholders, relative filesystem paths, missing
existing conda environments, or an effective intake hash that differs from the
canonical workflow.

## Required References

Read and follow:

- `docs/datasets/data-contract.md`
- `docs/datasets/stomicsdb-localization-workflow.md`
- `docs/datasets/public-data-research-case-extraction.md`
- `contracts/prompts/curation/stomicsdb_round2b_bundle_validation.md`
- `contracts/prompts/curation/dispatch_stomicsdb_round2b_bundle_worker.md`

Recompute the five required canonical hashes before dispatch:

- `docs/datasets/stomicsdb-localization-workflow.md`
- `docs/datasets/data-contract.md`
- `contracts/prompts/curation/stomicsdb_round2b_bundle_validation.md`
- `contracts/prompts/curation/dispatch_stomicsdb_round2b_bundle_worker.md`
- `contracts/prompts/curation/dispatch_stomicsdb_round2b_batch.md`

Reject the batch before creating worker windows if any recomputed value differs
from `contract_hashes`.

## Coordinator Protocol

1. Confirm Round 2A completion evidence before dispatch. Do not start Round 2B
   from a partial or still-running download state.
2. Reconcile every approved localization-queue row to one bundle assignment.
   For each bundle, generate `expected_target_paths` from acquisition-plan
   `target_path` values under that bundle's approved target prefix. Validate
   only expected physical-file completeness from this list; do not persist a
   `resource_ref` to TSV-row mapping or create a coverage sidecar. Each
   approved bundle is dispatched exactly once per attempt.
3. Permit parallel execution only for unique bundles with nonoverlapping staging
   and canonical paths.
4. Pre-create unique absolute staging directories and instantiate the
   single-worker wrapper without placeholders for every dispatched bundle.
5. Validate returned staged generations against the Round 2B protocol and data
   contract.
6. Publish extracted content first when present and publish
   `localization.yaml` last while holding the applicable bundle lock.
7. Redispatch retryable local failures with a new attempt number. If a worker
   returns `worker_status: awaiting_environment`, do not publish
   `localization.yaml`; retry
   with another already existing conda environment or prefix. Treat externally
   blocked bundles as terminal only when the staged `localization.yaml` is
   valid and records a blocker that truly requires external access, credentials,
   an unavailable service, or an unrecoverable remote object.
8. Continue until every approved bundle has terminal `LOCALIZED` or
   `BLOCKED_EXTERNAL` status.
9. Enforce the global barrier: Round 3 case construction must not start until
   every approved bundle has a terminal Round 2B `localization.yaml`.

## Boundary

Do not install dependencies, create environments, reconstruct TSV coverage,
create case IDs, assign `DATA_READY`, write HVUs, create dual-chain output, or
add audit artifacts.

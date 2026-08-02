# Dispatch: STOmicsDB Round 1 Resource Selection Worker

This is the single-owner assignment wrapper. It is not the selection protocol.

## Required Assignment

Provide a fully instantiated YAML object with no unresolved placeholders:

```yaml
selection_dispatch_generation_id:
assignment_id:
attempt_number:
owner_type:
owner_id:
repository_workdir:
nas_data_root:
selection_staging_directory:
canonical_owner_directory:
input_inventory_path:
input_inventory_sha256:
review_protocol_sha256:
human_resolution_receipt:
```

`owner_type` is `dataset | paper`. Dataset assignments use the owner
`files.jsonl` as `input_inventory_path`; paper assignments use the owner
`resource_links.yaml`. All filesystem paths are absolute except
`input_inventory_path`, which is NAS-data-root-relative. The coordinator must
pre-create a unique staging directory before dispatch.

## Required References

Read and follow:

- `docs/datasets/data-contract.md`
- `docs/datasets/stomicsdb-localization-workflow.md`
- `contracts/prompts/curation/stomicsdb_round1_resource_selection.md`

The resource-selection protocol is the sole owner of execution behavior. This
wrapper owns only assignment validation and dispatch boundaries.

## Required Response

Repeat `selection_dispatch_generation_id`, `assignment_id`, and
`attempt_number` exactly as assigned. Include the fixed owner identity, absolute
staged path, proposed NAS-root-relative manifest path, proposed queue rows, and
validation receipts using this response contract:

```yaml
selection_dispatch_generation_id:
assignment_id:
attempt_number:
owner_type:
owner_id:
selection_status:
staged_generation_id:
staged_manifest_path:
proposed_manifest_path:
candidate_queue_rows:
decision_counts:
validation_receipts:
human_review_request:
```

`selection_status` is `AUTO_APPROVED | NEEDS_HUMAN_REVIEW | HUMAN_APPROVED`.
`human_review_request` is required for `NEEDS_HUMAN_REVIEW` and null otherwise.
Candidate queue rows are publishable only for `AUTO_APPROVED` and
`HUMAN_APPROVED` manifests.

## Boundary

Handle only the assigned owner inventory. Do not write registries or canonical
paths, download data/code/supplements, inspect resource object contents, make
scientific admission decisions, create Round 2 `localization.yaml` manifests, or
return findings in place of a staged selection manifest.

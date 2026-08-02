# Dispatch: STOmicsDB Round 1 Article Worker

This is the single-article assignment wrapper. It is not the stage protocol.

## Required Assignment

Provide a fully instantiated YAML object with no unresolved placeholders:

```yaml
dispatch_generation_id:
assignment_id:
attempt_number:
paper_id:
source_doi:
normalized_doi:
linked_stds:
repository_workdir:
nas_data_root:
paper_staging_directory:
dataset_staging_directories:
canonical_paper_directory:
canonical_dataset_directories:
```

`linked_stds` is the complete duplicate-free list for the fixed paper.
`dataset_staging_directories` and `canonical_dataset_directories` are mappings
with exactly one absolute path for every listed STDS ID. All filesystem paths
are absolute. The coordinator must pre-create a unique paper staging directory
and unique dataset staging directories before dispatch.

## Required References

Read and follow:

- `docs/datasets/data-contract.md`
- `docs/datasets/stomicsdb-localization-workflow.md`
- `docs/datasets/public-data-research-case-extraction.md`
- `contracts/prompts/curation/stomicsdb_round1_article_localization.md`

The worker protocol is the sole owner of execution behavior. This wrapper owns
only assignment validation and dispatch boundaries.

## Required Response

Repeat `dispatch_generation_id`, `assignment_id`, and `attempt_number` exactly as
assigned. Return a complete staged generation, a valid externally caused
`partial` staged package, an `awaiting_human_review` identity-conflict response,
or a terminal `failed` package authorized by coordinator-recorded human
adjudication. Include the fixed paper ID, all linked STDS IDs, absolute staged
paths, and proposed NAS-root-relative manifest paths using this response
contract:

```yaml
dispatch_generation_id:
assignment_id:
attempt_number:
paper_id:
linked_stds:
paper_status:
dataset_statuses:
staged_generation_id:
publication_proposal:
validation_receipts:
human_review_request:
```

`dataset_statuses` contains exactly one independently determined status for
every linked STDS ID. `human_review_request` is required for
`awaiting_human_review` and null otherwise.

## Boundary

Handle only the assigned paper and its declared linked datasets. Do not write
registries or canonical paths, download data/code/supplements, make scientific
admission decisions, or return findings in place of a terminal package.

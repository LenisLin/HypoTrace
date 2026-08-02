# STOmicsDB Round 1 Resource Selection Protocol

## Purpose

Use this mandatory curator protocol to stage one metadata-only
`resource_selection.yaml` for a single STOmicsDB owner entity: either one
dataset or one paper. The stage runs only after exact Round 1 closure for the
paper, dataset, and linkage-edge counts declared by the effective intake
manifest.

## Required Inputs

- One fixed `owner_type`: `dataset | paper`.
- One fixed `owner_id`: an STDS ID for datasets or a DOI-derived `paper_id`.
- Absolute `repository_workdir` and `nas_data_root` paths.
- One unique absolute `selection_staging_directory`.
- Absolute canonical owner directory.
- NAS-root-relative `input_inventory_path`.
- SHA-256 of the input inventory.
- SHA-256 of this resource-selection protocol.
- Effective intake generation ID, manifest SHA-256, declared paper count,
  dataset count, linkage-edge count, and companion hashes.

Reject an assignment with missing values, unresolved placeholders, relative
filesystem paths, paths outside the declared repository or NAS roots, mismatched
owner type and inventory path, or an input-inventory hash mismatch.

## Required Reads

Before acting, read:

- `docs/datasets/data-contract.md`
- `docs/datasets/stomicsdb-localization-workflow.md`
- `contracts/prompts/curation/stomicsdb_round1_resource_selection.md`
- the fixed owner manifest.
- for dataset owners: the complete canonical `files.jsonl`.
- for paper owners: the complete canonical `resource_links.yaml`.

Do not read resource object bytes. Do not open H5, H5AD, RDS, archive, image,
or other data/code objects. Do not download resources, follow transfer links for
content, inspect scientific results, create case IDs, evaluate `DATA_READY`, or
write Round 2 bundle manifests.

## Execution Protocol

1. Verify the owner has a current-generation terminal Round 1 manifest and that
   the effective intake's declared Round 1 accounting has already closed.
2. Parse the source inventory using standard JSONL or YAML parsing. Reject
   duplicate resource identifiers or malformed records as retryable local
   failures; do not silently skip records.
3. Build exactly one `resource_ref` for every inventory record using the data
   contract's canonical forms.
4. Classify each inventory record from metadata only: filename, role, size,
   access state, locator level, resolution status, declared kind, owner, and
   linkage metadata.
5. Assign exactly one decision to every source inventory record:
   `retain`, `drop`, or `review`.
6. Use `retain` only for deterministic input resources required for a logical
   bundle: one clearly identified processed expression object over an equivalent
   raw expression object; required coordinates, images, scalefactors, metadata,
   platform support, reference inputs; and nonduplicated code resources.
7. Use `drop` only for clear analysis outputs, visualization/results artifacts,
   logs, reports, or demonstrably duplicate equivalents.
8. Use `review` for uncertain equivalence, processed/raw ambiguity, shared
   ownership conflicts, nonconcrete locators, incomplete role metadata, or any
   case where a deterministic metadata-only decision would require inspecting
   object contents.
9. Group retained resources into candidate logical bundles with canonical
   `bundle_type`, `owner_type`, `owner_id`, sorted `linked_paper_ids`, sorted
   `resource_refs`, and NAS-root-relative `target_directory` proposals. Compute
   proposed `bundle_id` values using the data-contract rule.
10. Write a staged `resource_selection.yaml` containing the exact contract from
    `docs/datasets/data-contract.md`.
11. Parse the staged YAML and verify: inventory SHA-256, protocol SHA-256,
    owner identity, one-to-one decision coverage, no duplicate `resource_ref`,
    candidate bundle consistency, sorted duplicate-free bundle resources, and
    no retained resource outside a candidate bundle.
12. Return staged absolute paths, NAS-root-relative manifest paths, validation
    receipts, candidate queue rows, and any human-review request to the
    coordinator. Do not write registries or canonical owner directories.

## Status Rules

Set `status: AUTO_APPROVED` only when every source inventory record has final
`retain` or `drop`, every retained resource belongs to a validated candidate
bundle, and `remaining_issue` is null.

Set `status: NEEDS_HUMAN_REVIEW` when at least one record requires `review`.
`remaining_issue` must identify the ambiguous equivalence, ownership,
processed/raw, locator-concreteness, or metadata-insufficiency reason. Candidate
queue rows from that owner remain unpublished until human resolution.

Set `status: HUMAN_APPROVED` only when the assignment includes
coordinator-recorded human resolution and every source inventory record has a
final `retain` or `drop` decision. The manifest must preserve the resolved
reason codes and cite the human-review receipt in `remaining_issue` or a
candidate-bundle note when relevant.

## Boundaries

This protocol decides only operational resource retention for Round 2 transfer
queues. It does not assert object readability, scientific usability,
sample-object linkage, primary/originating-paper status, scientific scope, case
admission, or `DATA_READY`. It must not create `localization.yaml`, download
data or code, create HVUs, create dual chains, or start Round 2.

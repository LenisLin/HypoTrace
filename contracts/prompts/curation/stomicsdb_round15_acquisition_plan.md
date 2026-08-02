# STOmicsDB Round 1.5 File-Level Acquisition Plan Protocol

## Purpose

Convert the fully approved bundle queue into one deterministic two-column download plan without transferring resource bytes.

## Inputs

- effective intake manifest and current-generation entity records;
- `registry/localization_queue.jsonl`;
- referenced `resource_selection.yaml`, `files.jsonl`, and `resource_links.yaml`;
- NAS data root.

## Output

- `registry/acquisition_plan.tsv` with exactly `source_url` and `target_path`.

## Required Behavior

1. Resolve each approved resource to concrete physical files.
2. Use direct HTTP or HTTPS URLs only.
3. Resolve code repositories to commit-fixed archive URLs.
4. Place each target under the approved bundle's `artifacts/` directory.
5. Return ambiguous expansions, non-equivalent alternatives, representation changes, and path collisions to human review.
6. Publish the TSV only when every approved resource is completely and unambiguously represented.
7. Validate the header, tab count, URL scheme, target containment, uniqueness, and absence of placeholders.
8. While materializing the plan, keep only a transient in-memory mapping from
   each approved `resource_ref` to its resolved TSV row or rows. Before
   publication, confirm that every approved `resource_ref` resolves to at least
   one row and that every row derives from an approved `resource_ref`. Discard
   the mapping after successful publication; do not persist it in a sidecar,
   dispatch state, audit artifact, or additional TSV column.

## Resolution Validation Examples

- A direct file URL may produce one row when it identifies the physical transfer object and its target is contained by the approved bundle's `artifacts/` directory.
- An accession must be expanded to all required direct physical file URLs before publication; an accession itself is not a valid `source_url`.
- A supplement landing page must be resolved to its direct file URL. Multiple non-equivalent supplement representations require human review.
- A code repository must resolve to an archive URL fixed to a specific commit; a repository root, branch archive, or moving tag is invalid.

## Boundary

Do not download resource bytes, open scientific objects, unpack archives, assign localization or readiness status, create cases, or construct dual chains. Do not add coverage columns, sidecar mappings, coverage reports, or audit artifacts. Publish only the two-column `registry/acquisition_plan.tsv`.

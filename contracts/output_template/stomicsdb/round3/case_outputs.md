# STOmicsDB Round 3 Case Output Template

This template is the sole accepted output contract for Round 3. It is a
documentation contract, not a machine schema.

An accepted `(article, STDS dataset)` job writes exactly:

```text
source_manifest.yaml
data/case_data_manifest.yaml
case_manifest.yaml
```

All persisted local paths are relative to
`/mnt/NAS_21T/ProjectData/HypoTrace_Data/`. Only results, data objects,
auxiliary resources, and links used by at least one case candidate may appear.
Unsupported results and unused records are omitted.

Formal output excludes process hashes, review findings, retries, statuses,
receipts, mapping grades, coverage ledgers, worker identities, and process
history. It includes the required upstream provenance hashes and generation
identifiers shown below.

## `source_manifest.yaml`

```yaml
source_manifest:
  stds_id:
  article_path:
  article_sha256:
  article_manifest_path:
  article_manifest_sha256:
  article_generation_id:
  article_title:
  results:
    - result_id:
      result_section:
      source_anchors:
        - type: figure | table | text
          locator:
      scientific_question:
      conclusion:
      analysis_steps:
        - input:
          method:
          output:
```

Assign `R01`, `R02`, ... in article Results order before filtering. Retained IDs
may therefore be non-contiguous. `result_section` and nonempty
`source_anchors` locate the result in the main article. Stable figure or panel,
table, and text locators are valid; supplementary-only analyses are excluded.
`analysis_steps` is an ordered, article-supported `input -> method -> output`
representation. The article path, raw-byte SHA-256, article-manifest path and
raw-byte SHA-256, and article generation ID must match the fixed dataset-local
article binding.

## `data/case_data_manifest.yaml`

```yaml
case_data_manifest:
  stds_id:
  dataset_binding:
    dataset_manifest: {path:, sha256:, generation_id:}
    source_manifest: {path:, sha256:, generation_id:}
    samples: {path:, sha256:}
    files: {path:, sha256:}
  data_objects:
    - data_id:
      path:
      role:
      data_context:
        organism:
        tissue_or_context:
        spatial_assay:
        sample_summary:
        available_metadata: []
      localization_bindings:
        - {path:, sha256:, generation_id:}
      expression_matrix:
        files: [{path:, format:, sha256:}]
        summary:
      coordinates:
        files: [{path:, format:, sha256:}]
        summary:
      image:
        files: [{path:, format:, sha256:}]
        summary:
      metadata:
        files: [{path:, format:, sha256:}]
        summary:
  auxiliary_resources:
    - resource_id:
      resource_name:
      expected_content:
      source_url:
      access_classification: anonymous_direct | nonanonymous_access | identified_not_directly_downloadable
      local_availability: absent | localized
      access_notes:
      localization_binding:
        package_manifest:
          package_id:
          path:
          sha256:
          generation_id:
        artifacts:
          - artifact_id:
            path:
            source_url:
            size_bytes:
            sha256:
        expected_content_coverage:
          status: complete
          items:
            - requirement:
              artifact_ids: []
              evidence:
          uncovered_requirements: []
  result_data_links:
    - result_id:
      data_inputs:
        - data_id:
          input_role: primary_spatial | reference | other_required
          sample_ids: []
          required_components:
            - component: expression_matrix | coordinates | image | metadata
              paths: []
      auxiliary_resource_ids: []
```

Each `Dxx` describes one coherent logical scientific dataset established by
inspection, not one physical file, sample, archive, or bundle. `path` is the
narrowest canonical dataset root owning the logical dataset. There is no
top-level `Dxx.format`; formats and SHA-256 values belong to component files.
`data_context` uses exactly the five fields shown above so downstream `S00`
construction has a stable, bounded study-context input.

Each of `expression_matrix`, `coordinates`, `image`, and `metadata` is either
`null` or a component object containing `files` entries with exact
NAS-data-root-relative `path`, `format`, and raw-byte `sha256`, plus a
lightweight `summary`. The expanded `expression_matrix` entry above defines
that common component shape. A component summary is limited to representation,
relevant sample coverage, joins or alignment, and the minimum observed schema
needed for downstream use.

Every `dataset_binding` path, hash, and generation ID must match the assigned
canonical dataset records. Every `localization_bindings` entry must name and
hash a parsed bundle `localization.yaml` and reproduce its `generation_id`.
Every component file must be declared by at least one of that `Dxx` object's
localization bindings.

Every retained result has exactly one `result_data_links` entry. Each
`data_inputs` entry states the scientific role, exact relevant sample IDs, and
the components and paths required for that result. Each nonempty
`required_components[].paths` list must be a subset of the referenced `Dxx`
component's `files[].path` values. Sample IDs must resolve through the bound
`samples.jsonl` and agree with the referenced component coverage.

An `Axx` identifies a necessary auxiliary input outside the assigned STDS
dataset package. It is not a `Dxx`. Formal `Axx` records use exactly one of the
three contract access classifications and `local_availability: absent |
localized`. Resource name, expected content, source URL, access classification,
and access notes remain fixed when an accepted case later binds a canonical
localization. `not_located` is valid temporary resource-access evidence, but it
makes each affected result unsupported and is never persisted as an `Axx`.

For `local_availability: absent`, `localization_binding` is null and no package,
artifact, hash, generation, or coverage binding may appear. For
`local_availability: localized`, `localization_binding` is a non-null single
object. `package_manifest` names and raw-byte hashes one immutable canonical
auxiliary `localization.yaml`, reproduces its package and generation IDs, and
never uses a staging path. Every bound artifact has exactly the five fields
`artifact_id`, `path`, `source_url`, `size_bytes`, and `sha256`; every value must
match the corresponding package-manifest artifact verbatim. The nonempty
`artifacts` list is an exact subset of the package artifacts required by this
`Axx`.

`expected_content_coverage.status` is exactly `complete`. Its nonempty `items`
map every requirement implied by `expected_content` to one or more bound
artifact IDs with concise structural evidence, and `uncovered_requirements` is
empty. Every bound artifact must be a readable regular file whose path, size,
and raw-byte SHA-256 validate through the package manifest. The package field
contract and first-publication rules are owned by the [Round 3 auxiliary
localization template](auxiliary_localization.md).

## `case_manifest.yaml`

```yaml
case_manifest:
  stds_id:
  source_manifest_path: source_manifest.yaml
  case_data_manifest_path: data/case_data_manifest.yaml
  case_candidates:
    - candidate_id: C01
      result_ids: []
      result_order: []
      spatial_data_ids: []
      auxiliary_resource_ids: []
      result_connections:
        - from_result_id:
          to_result_id:
          from_output:
          to_input:
```

Every formal record is referenced by at least one `Cxx`. A candidate's eligible
local data IDs are the union of the `data_inputs[].data_id` values declared by
its member results. For every member result, collect the `Dxx` values whose
`input_role` is `primary_spatial`; every member must declare the same nonempty
set, and `spatial_data_ids` must equal that common set exactly. Auxiliary
resource IDs resolve through the same member-result links.

A one-result candidate has an empty `result_connections` list. A multi-result
candidate uses the common primary spatial set throughout and contains explicit,
acyclic output-to-input connections. `result_order` preserves article order and
contains exactly the candidate's result IDs.

The three `stds_id` values match, the two manifest paths have the exact values
shown above, and every cross-file reference resolves. All required path hashes
are raw-byte SHA-256 values. The accepted three-object tree must preserve the
article, dataset, localization, file, sample, component-subset, and common
spatial-ID invariants stated in this contract.

Changing an accepted `Axx` from absent to localized is a full three-file
post-publication case transaction, never an in-place manifest edit. Only the
target `Axx.local_availability` and `localization_binding` may change; all
scientific `Rxx`, `Dxx`, and `Cxx` objects and every other case field remain
semantically identical. The unchanged `source_manifest.yaml` and
`case_manifest.yaml` bytes are preserved exactly. The transaction retains
recoverable prior bytes, checks preconditions and locks, rolls back partial
publication, and marks prior dual-chain input bindings stale.

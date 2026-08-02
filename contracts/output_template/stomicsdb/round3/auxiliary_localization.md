# STOmicsDB Round 3 Auxiliary Localization Template

This template is the sole field contract for canonical localization of an
auxiliary resource retained by an accepted Round 3 case. It is a documentation
contract, not a machine schema. Acquisition success, a source URL, or a file in
download staging is evidence for localization; none is itself a canonical
localization or a `DATA_READY` decision.

## Canonical package

One immutable auxiliary-resource generation is published under:

```text
raw_data/public_database/stomicsdb/auxiliary_resources/
  <package_id>/
    generations/
      <generation_id>/
        localization.yaml
        artifacts/
          <filename>
```

`package_id` is the stable canonical resource ID, normally the retained
`R3AUX...` inventory ID. `generation_id` is unique, filesystem-safe, and
immutable after publication. There is no mutable `current` symlink or manifest.
Every persisted path is relative to the NAS data root. A path under `staging/`,
including `staging/round3_auxiliary_downloads/`, is never canonical and is
invalid in a case localization binding.

## `localization.yaml`

```yaml
auxiliary_localization_manifest:
  package_id:
  generation_id:
  localization_status: LOCALIZED
  resource_identity:
    resource_name:
    source_url:
  expected_content:
  acquisition_bindings:
    inventories:
      - path:
        sha256:
        inventory_resource_id:
    successful_runs:
      - run_id:
        events_path:
        sha256:
  artifacts:
    - artifact_id:
      path:
      source_url:
      format:
      role:
      size_bytes:
      sha256:
  validation:
    artifact_count:
    acquisition_bindings_verified: true
    all_artifacts_regular_files: true
    all_artifacts_readable: true
    all_artifact_sizes_verified: true
    all_artifact_sha256_verified: true
    all_artifact_paths_canonical: true
```

The package repeats the resource name, stable source URL, and expected content
from the retained resource inventory. The inventory and run paths are immutable
NAS-data-root-relative evidence paths. Their hashes cover their complete raw
bytes. Every `successful_runs` record names a run whose terminal event proves
successful acquisition of the package's declared artifacts; partial or failed
events cannot be combined into a successful run binding.

Each `artifact_id` is unique within the package and stable for the acquired
transfer object, normally its `R3FILE...` ID. `path` is inside this exact
generation's `artifacts/` directory. `source_url` is the non-secret source URL
bound by the acquisition evidence. `format` and `role` are nonempty observed
descriptions; they do not assert biological validity or reproduce a result.
`size_bytes` and `sha256` bind the canonical regular-file bytes.

`localization_status` has the single terminal value `LOCALIZED`. A manifest is
valid only when its package and generation IDs agree with its path, every
artifact is a readable regular file, every size and raw-byte SHA-256 matches,
all artifact paths stay within the immutable generation, the declared artifact
count is exact, and all acquisition bindings resolve and hash correctly.
Missing or invalid material produces no canonical generation; it must not be
represented by another status in this manifest.

## Combined publication and case binding

Canonical package first-publication and adoption by accepted cases are two
ordered phases of one recoverable
`round3_auxiliary_localization_binding` transaction, not distinct transactions.
The transaction builds every complete package generation under unique
NAS-resident staging. Artifact bytes are materialized before each manifest by a
byte-stream copy or a verified same-filesystem reflink. Do not use `cp -a`,
`rsync -a`, an archive/tree copy, a metadata-preserving copy, or a hardlink to
mutable download staging. Preserve the download inventory, run events, and
original download objects as acquisition evidence.

After all artifact paths, sizes, and hashes are fixed, serialize
`localization.yaml` last. Reopen and parse the manifest, validate all identity,
path, acquisition, count, size, and hash invariants against every staged tree,
and stage and validate every complete three-file case replacement. Acquire the
complete package and case lock set, recheck all destination-absence and current
case-byte preconditions, then publish and reopen every package generation under
the locks. Only after all package generations validate canonically may the
transaction replace any case tree.

An accepted Round 3 case remains exactly three files. A localized case-local
`Axx` preserves its original resource name, expected content, source URL,
access classification, and access notes, and binds one canonical package using
the [Round 3 case output template](case_outputs.md). `Axx` remains an auxiliary
input and is never converted into a `Dxx`.

The same transaction replaces each complete three-file case tree through the
data-contract post-publication protocol. It may change only the target
`Axx.local_availability` and its localization binding. It preserves the exact
scientific `Rxx`, `Dxx`, and `Cxx` objects, all references and identifiers, and
all other case fields. The prior case bytes remain recoverable. After every case
replacement validates, the transaction marks every dual chain bound to the
replaced case bytes stale. `COMMITTED` is permitted only after all packages,
case replacements, and stale-chain handling validate successfully.

Any failure after canonical package publication triggers compensation within
the same transaction: restore every replaced case from its hashed backup, then
delete only package generations created by this transaction that no restored or
current case references. Reopen and validate the restored cases, verify that no
current case references a deleted generation, and record `ROLLED_BACK`. A
failed restoration is not a valid terminal rollback, and partial package/case
publication must never be reported as `COMMITTED`.

`DATA_READY` is derived downstream only after every referenced `Dxx` binding and
every required localized `Axx` package, artifact subset, and expected-content
coverage record validate. A URL, successful download, staging file, or package
manifest without a valid case binding is insufficient.

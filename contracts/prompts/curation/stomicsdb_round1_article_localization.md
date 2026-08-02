# STOmicsDB Round 1 Article Localization Worker Protocol

## Purpose

Use this mandatory curator protocol to stage one DOI-deduplicated Round 1 paper
generation and the article package for every linked STDS record. One invocation
handles exactly one fixed `paper_id`; all of that paper's linked STDS IDs belong
to the same invocation.

## Required Inputs

- One fixed `paper_id`, `source_doi`, and `normalized_doi`.
- The complete, duplicate-free `linked_stds` list.
- Absolute `repository_workdir` and `nas_data_root` paths.
- One unique absolute `paper_staging_directory`.
- One unique absolute dataset staging directory for every linked STDS ID.
- Absolute canonical paper and dataset directories.

Reject an assignment with missing values, relative filesystem paths,
unresolved placeholders, duplicate linked STDS IDs, paths outside the declared
repository/NAS roots, or overlapping staging/canonical destinations.

## Required Reads

Before acting, read:

- `docs/datasets/data-contract.md`
- `docs/datasets/stomicsdb-localization-workflow.md`
- `docs/datasets/public-data-research-case-extraction.md`
- `contracts/prompts/curation/stomicsdb_round1_article_localization.md`
- the frozen intake, paper registry row, linkage edges, linked dataset
  manifests, and any existing canonical or staged generation for this paper.

## Execution Protocol

1. Reconcile existing canonical and staged state by `paper_id`, normalized DOI,
   generation, linked STDS coverage, hashes, and source locators. Resume a valid
   incomplete staging generation; never overwrite a valid canonical generation
   in place.
2. Verify the paper identity against the DOI, article landing page, title, and
   independent bibliographic evidence. A paper-identity conflict returns
   `awaiting_human_review` with the conflicting evidence and no terminal
   scientific or identity decision. Only a coordinator-recorded human
   adjudication may correct the assignment or authorize a terminal `failed`
   paper package and `IDENTITY_FAILED` dataset article manifests. Transient
   lookup, parsing, and transport failures remain retryable.
3. For every linked STDS ID, validate the existing canonical dataset package
   against the current Round 1A contract. Reuse a valid current-generation
   package. Classify a legacy, incomplete, checksum-mismatched, or missing
   package as `migration_required` or `retryable`, then stage the files needed to
   bring that dataset to a valid Round 1A terminal state. Paper completion never
   substitutes for dataset completion. Preserve the complete source inventory
   contract; do not download dataset data objects.
4. Inspect existing lawful article sources before network retrieval. Reuse an
   already valid canonical or staged PDF and do not redownload it.
5. If no valid PDF exists, search the lawful anonymous routes in the order and
   under the access restrictions defined by the STOmicsDB localization workflow,
   or use an operator-supplied PDF only as `operator_provided_verified_pdf`
   after the same validation passes. Do not bypass access controls and do not
   synthesize a PDF from HTML, XML, or text.
6. Validate the PDF using only the workflow completion criteria: signature,
   page count, text extractability, DOI/title identity, size, SHA-256, and
   linked-dataset byte identity. Record its source locator or operator-provided
   status, reported size when available, local size, SHA-256, and article
   identity evidence. Preserve the raw bytes.
7. Inspect the article's resource disclosures and stage only locator records in
   `resource_links.yaml`. Do not download data, code, supplements, or project
   resources.
8. Stage the canonical paper package, including `source/article.pdf` when
   localized. The paper `source_manifest.yaml` owns that file's canonical hash.
9. For every linked STDS ID, stage `article/article_manifest.yaml` with the
   canonical field names from the data contract. When a canonical PDF is
   localized, propose an actual regular `article/article.pdf` materialization
   using hard link, reflink, or byte-identical copy. The dataset manifest's
   `companion_records` must include the staged article manifest.
10. For localized PDFs, require identical size and SHA-256 for the canonical PDF
    and every staged dataset-local PDF. Reject symlinks and pointer-only records.
    For `BLOCKED_EXTERNAL` or adjudicated `IDENTITY_FAILED`, create no PDF
    placeholder and enforce the null transfer fields required by the data
    contract.
11. Parse every YAML/JSONL record, verify generation consistency, companion
    checksums, linkage-edge coverage, regular-file status, and all required
    fields. Source records and companion records must use canonical
    NAS-root-relative paths, never staging paths. Write companion records first
    and the entity manifest last within staging.
12. Return staged absolute paths, manifest-relative paths, validation receipts,
    a publication proposal, and independent `paper_status` and
    `dataset_statuses` maps covering every linked STDS ID to the coordinator. Do
    not write registries, acquire publish locks, or write canonical files.

## Retry, Resume, and Terminal States

Local implementation errors, invalid downloads, parse failures, checksum
mismatches, transient transport failures, and incomplete linked-STDS coverage
remain retryable. Repair or resume from staging. Do not classify them as
external blockers.

Return `complete` only with a validated canonical PDF at
`papers/<paper_id>/source/article.pdf` and a valid staged dataset-local package
with byte-identical `datasets/<STDS_ID>/article/article.pdf` for every linked
STDS ID. Return `partial` only after DOI identity and usable article text are
verified and all authorized lawful PDF routes plus any available
operator-provided route are exhausted; stage a valid `BLOCKED_EXTERNAL` article
manifest for every linked dataset, record attempted routes and the external
condition, and do not create PDF placeholders.

A paper-identity conflict returns `awaiting_human_review` with the conflicting
evidence and no terminal scientific or identity decision. Only a
coordinator-recorded human adjudication may correct the assignment or authorize
a terminal `failed` paper package and `IDENTITY_FAILED` dataset article
manifests. Transient lookup, parsing, and transport failures remain retryable.
Every terminal response includes independent paper and dataset status maps, and
the dataset map covers every linked STDS ID.

## Boundaries

Work only on the assigned paper and linked datasets. Do not write registry or
canonical paths. Do not download data, code, supplements, or scientific result
artifacts. Do not decide primary/originating-paper status, sample-object
linkage, scientific scope, claim truth, causality, case admission, or
`DATA_READY`. Manifest paths remain NAS-root-relative even though execution
paths are absolute.

Do not return after producing findings. Return only a complete staged generation,
a valid externally caused `partial` package after all lawful PDF routes are
exhausted, an `awaiting_human_review` identity-conflict response, or a terminal
`failed` package authorized by coordinator-recorded human adjudication.

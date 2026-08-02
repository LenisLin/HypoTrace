# STOmicsDB Localization Workflow

## Purpose and Boundaries

This document is the canonical executable operational contract for the
STOmicsDB intake. The active research scope is the exact ordered
`selected_stds_ids` allowlist in the current intake manifest and must match the
canonical list in [Public-Data Research Case
Extraction](public-data-research-case-extraction.md). Every stage rejects an
STDS ID that is not present in that allowlist.

The current intake manifest records `generation_id`, nullable
`parent_generation_id` and `parent_manifest_sha256`, `freeze_timestamp`,
`scope_policy`, `selected_stds_ids`, `selected_stds_count`,
`deduplicated_paper_count`, `linkage_edge_count`, and `companion_records`.
`registry/intake_generations/` retains only the current frozen generation after
an approved hard scope reset. Historical intake counts, transfer sizes, queue
sizes, and deleted generations are not operational authorities.

Round 1 discovers and localizes source and locator evidence. Round 1.5 selects
logical bundles and resolves them to a file-level acquisition plan. Round 2A is
an operator-started background download that transfers approved data, code, and
metadata artifacts without semantic inspection. Round 2B processes one approved
bundle per assignment and starts only after Round 2A completes. None of these
stages creates case IDs, `DATA_READY` records, hypothesis-verification units
(HVUs), or dual chains. Object readability sufficient for scientific use,
case extraction, and later processing remain outside this workflow.

Canonical localization of auxiliary resources retained by accepted Round 3
cases is a later, separately authorized handoff. Its fields are owned by the
[Round 3 auxiliary localization
template](../../contracts/output_template/stomicsdb/round3/auxiliary_localization.md),
and its storage and transaction rules are owned by the [data
contract](data-contract.md). A completed Round 2A or Round 3 auxiliary download
never substitutes for that canonical handoff.

Except for the operator-started Round 2A transfer program and launcher, no
project-local script is a Round 3 dependency or helper. Round 3 reads the
dataset-local article, manifests, and actual canonical data directly in one
dataset-scoped model context. Standard readers and structured parsers may be
used directly, but they do not replace article reading or scientific judgment.

## Worker Execution Contract

This workflow uses light audit and heavy execution. There is no standalone audit
worker, audit stage, audit summary, rejected-item log, or findings-only terminal
output. Workers perform only the identity, parsing, completeness, and transfer
checks required to select the next action and prove a valid terminal state.

A failed check triggers repair, retry, resume, approved-locator reconstruction,
human review when scope would change, or coordinator redispatch. Canonical
records retain only source facts, minimal completion receipts, approved queue
rows, and terminal bundle manifests.

Every worker follows this mandatory loop exactly:

```text
read fixed input -> inspect staging -> perform next concrete action -> minimal completion checks -> repair/retry/resume -> stop only at valid terminal -> atomically publish latest canonical
```

Workers repair actionable failures and continue from staging; they do not emit
findings, recommendations, audit reports, or status summaries in place of
completing work. Human escalation is limited to
identity conflicts, scope changes, restricted access, processed-input
classification, paper-role adjudication, and changes to the frozen intake.
After an effective intake generation exists, changes to the active set require
an explicit coordinator-controlled scope replacement. Discovery, retries, or
historical records do not expand the frozen allowlist.

## Round 1 Article Worker Pool

The Round 1 execution pool contains one coordinator and the article-worker
windows currently available to that coordinator. Before dispatch, discover the
available worker capacity. Dispatch up to the smaller of the actionable-paper
count and the available worker-window count. Do not impose or reserve an
artificial fixed worker count.

Keep every available worker slot occupied while actionable work remains,
subject to assignment uniqueness, publication safety, per-host network
throttling, and external rate limits. A temporary reduction in available
capacity pauses only the affected dispatch; it does not change queue state,
make work terminal, or justify an early batch return.

Retain the ordered window lifecycle:

For every returned worker assignment:

1. Persist the returned assignment and validation receipts.
2. Mark the worker window `close_required`.
3. Close the worker window and confirm capacity release.
4. Validate and publish, place in human review, or requeue the generation.
5. Open a replacement window when actionable work and worker capacity remain.

A retry always uses a new worker window. A local failure does not reduce
available worker capacity while actionable work remains.

Before dispatch, the coordinator creates one unique absolute paper staging
directory and one unique absolute dataset staging directory per linked STDS
record. Workers receive and use absolute repository, NAS, staging, and canonical
filesystem paths; paths written into manifests remain NAS-data-root-relative.
Workers never write registries or canonical packages. The coordinator alone
validates staged generations, holds publication locks, and publishes canonical
records with the manifest last.

Worker capacity is independent of network throttling. The coordinator caps
concurrent HTTP requests per host, honors source rate limits and retry guidance,
and schedules other hosts or non-network validation while a host is at its cap.
A host cap does not reduce the number of available article worker assignments.

## Round 1A: Dataset Web Localization

The worker unit is one frozen STDS record. The worker captures the dataset
summary, data, sample, and related-project pages together with authorized
metadata responses. It expands every pagination route needed to produce a
complete staged file inventory.

The worker publishes the dataset source snapshot, `dataset_manifest.yaml`,
`source_manifest.yaml`, `samples.jsonl`, and complete canonical `files.jsonl`.
`files.jsonl` is the complete canonical inventory of file identities, metadata,
roles, and locators discovered through the fully expanded STOmicsDB record. It is
source metadata, not an audit report and not a download decision. Automated
resource selection does not delete rows from `files.jsonl`; it determines which
resource references may enter approved logical bundles.

A Round 1 local implementation defect, incomplete pagination pass, parse failure,
or transient transport failure is nonterminal. The worker must repair or retry
it. Terminal `failed` is permitted only when identity or required inventory
completion remains impossible after all authorized public routes and actionable
repairs have been exhausted, with the unresolved external condition recorded in
the entity manifest.

The dataset `source_acquisition_status` is `complete | partial | failed`:

- `complete`: identity verified, required pages parsed, pagination exhausted,
  and complete inventory published.
- `partial`: identity and complete inventory verified, but a non-inventory
  source remains externally unavailable.
- `failed`: identity or complete inventory cannot be established after
  retryable causes are exhausted.

`dataset_manifest.yaml` includes the minimal completion receipts
`pagination_complete` and `discovered_file_count`.

## Round 1B: Paper Localization

The worker unit is one DOI-deduplicated paper. The worker resolves DOI identity
and acquires the article landing page plus the required article PDF.
It records concrete or expandable data, code, supplement, repository, and
project locators in `resource_links.yaml`.

Round 1B requires an identity-verified article PDF acquired either through an
anonymous lawful route or as an `operator_provided_verified_pdf`. Search lawful
routes in this order: publisher PDF, PubMed Central or Europe PMC PDF, an
official journal repository, and an author/institutional public manuscript
repository. Do not bypass authentication, CAPTCHA, paywalls, institutional
access, or project permissions. An operator-provided PDF may satisfy the PDF
requirement only after the same identity and file checks pass.

Do not synthesize a PDF from HTML or XML. HTML, XML, and plain text remain
supporting article sources but do not satisfy the PDF requirement.

`complete` requires DOI identity, article landing-page evidence, a validated PDF,
resource-disclosure inspection, canonical paper publication, and materialization
of the PDF into every linked dataset.

`partial` applies when DOI identity and usable article text are verified but no
lawful anonymous PDF remains available after all authorized routes are
exhausted. Record the attempted routes and external condition without treating
it as a local implementation failure.

Validate every candidate PDF before publication using only these completion
criteria:

1. The file starts with a valid PDF signature.
2. `pdfinfo` succeeds and reports at least one page.
3. `pdftotext` succeeds on at least the first pages.
4. DOI, title, or equivalent bibliographic evidence verifies article identity.
5. Local size and SHA-256 are recorded.
6. The paper PDF and every linked-dataset materialization have byte-identical
   size and SHA-256.

Raw PDF bytes are never rewritten. Do not reintroduce removed PDF-specific
checks, fields, statuses, or explanatory requirements beyond this contract.

Round 1B does not download data, code, or supplements. Its
`source_acquisition_status` is `complete | partial | failed`:

- `complete`: all requirements in the `complete` contract above are satisfied,
  including canonical publication to `papers/<paper_id>/source/article.pdf`
  and byte-identical linked-dataset publication to
  `datasets/<STDS_ID>/article/article.pdf`.
- `partial`: the identity-and-text conditions in the `partial` contract above
  are satisfied, but no lawful anonymous PDF is available.
- `failed`: a usable canonical article source cannot be verified after
  retryable causes are exhausted, or a paper-identity conflict has
  coordinator-recorded human adjudication authorizing a terminal failed package.

Local implementation defects, parse failures, and transient transport failures
are nonterminal and must be repaired or retried. `paper_manifest.yaml` includes
the minimal completion receipts `doi_identity_verified`, `landing_page_status`,
`full_text_status`, and `resource_disclosure_inspection_status`.

Both `dataset_manifest.yaml` and `paper_manifest.yaml` include this publication
receipt:

```yaml
generation_id:
companion_records:
  - path:
    sha256:
```

Each `path` is a canonical NAS-data-root-relative path, never a staging path.
`companion_records` covers the canonical metadata records published with the
entity manifest; `source_manifest.yaml` separately inventories and hashes files
in the source snapshot. Successful canonical publication deletes the staging
generation unless it is retained for retry, human review, or a valid
external-partial receipt.

## Round 1.5A: Automated Resource Selection and Exception Review

This stage starts only after exact Round 1 closure for the effective intake
manifest's declared paper, dataset, and linkage-edge counts, with companion
hashes matching the effective generation. It is metadata-only. The coordinator
and selection workers may read `files.jsonl`, `resource_links.yaml`, filenames,
roles, sizes, access states, and locator metadata. They must not open H5, H5AD,
RDS, archive, image, or other resource objects; download resources; inspect
scientific results; alter internal derived annotations; remove inventory rows;
create case IDs; evaluate `DATA_READY`; or start Round 2.

Candidate resource references from complete owner inventories are grouped by
dataset, paper, sample, role, and locator evidence before bundle selection. Each
source inventory record receives exactly one decision in the owner
`resource_selection.yaml`.

Automatic approval is permitted only for deterministic metadata-level
decisions:

- Retain one clearly identified processed expression object over an equivalent
  raw expression object.
- Retain required coordinates, images, scalefactors, metadata, platform support,
  reference inputs, and nonduplicated code resources needed to make the proposed
  logical bundle complete.
- Drop clear analysis-result outputs and demonstrably duplicate equivalents.

Exception review is required for uncertain equivalence, processed/raw ambiguity,
shared ownership conflicts, and nonconcrete locators. A `retain | drop | review`
decision does not establish `sample_object_linkage_verified`,
primary/originating-paper status, scientific scope, case admission, object
usability, or `DATA_READY`.

Automatically approved bundles may be published directly to
`registry/localization_queue.jsonl` with `approval_basis: automatic_rule`.
Ambiguous bundles remain unpublished until human resolution converts every
source inventory record to a final `retain` or `drop` decision; those queue rows
use `approval_basis: human_review`. Transient review entries are removed after
resolution. The final approved queue is published only after every retained
resource belongs to a validated logical bundle and no unresolved review row
remains.

If an approved processed object cannot be resolved to a direct transfer object,
the coordinator first tries verified public locators for the same object.
Substitution with a raw expression object changes the selected input
representation and must return to human review.

## Round 1.5B: File-Level Acquisition Plan

After the approved `registry/localization_queue.jsonl` is complete, resolve every approved resource to one or more concrete transfer objects and publish `registry/acquisition_plan.tsv`.

The TSV has exactly two tab-separated columns:

source_url	target_path

Each row represents one physical file. `source_url` must be a direct HTTP or HTTPS file URL. Accessions, landing pages, repository roots, directory listings, and unresolved placeholders are invalid. Code resources must use an archive URL fixed to a specific commit. `target_path` is NAS-data-root-relative, unique, and located inside the approved bundle's `artifacts/` directory.

Do not publish a partial plan. Ambiguous expansion, multiple non-equivalent candidates, representation changes, or target-path conflicts return to human review. Approved-resource coverage is verified only while the TSV is being generated through a transient in-memory mapping from approved `resource_ref` values to TSV rows. Discard that mapping after successful validation. Do not add TSV columns, sidecars, long-lived coverage mappings, or independent audit artifacts. This stage does not transfer resource bytes or inspect scientific contents.

A locator-only correction after plan publication is a coordinator-owned,
versioned transaction. It binds the previous plan hash, identifies the exact
existing `target_path`, verifies the expected previous `source_url`, and may
replace only that URL. It preserves target path, bundle membership, resource
identity, and selected representation; validates the complete revised plan for
duplicate URLs and targets; sanitizes secret-bearing URL components; and
publishes atomically with a NAS-resident receipt. An object, ownership, target,
or representation change is not a locator correction and returns to resource
selection or human scope review.

## Round 2A: Operator-Started Background Download

Round 2A is implemented by `scripts/stomicsdb_round2_download.py`. The operator
starts it manually through `nohup`, `tmux`, or `screen`; publishing an
acquisition plan does not start transfer. `--validate-only` parses and validates
the complete plan without creating target directories or opening network
connections. The downloader reads `acquisition_plan.tsv` and writes downloads
through same-directory `.part` files.

The downloader supports HTTP Range resume, restarts safely when a server
ignores or misreports Range, rejects HTML error responses for non-HTML targets,
checks response length when available, computes SHA-256 for the completed local
file, and atomically renames the `.part` file to its final target. Existing
final files are skipped unless overwrite is explicitly requested. Controlled
concurrency, timeout, retry count, and retry backoff are command-line options.
One failed row does not remove completed files; any unresolved failure produces
a non-zero process exit.

The script writes downloaded files and machine-readable JSONL operational
events to stdout/stderr only. An operator may redirect those streams to a NAS
log file when starting the background process.
`scripts/start_stomicsdb_round2_download.sh` is the canonical convenience
launcher: it validates the complete plan first, then starts the Python
downloader with `nohup`, controlled worker count, and NAS-resident JSONL/PID
files. Merely publishing the script or plan never invokes the launcher.
It does not unpack archives, inspect scientific objects, publish
`localization.yaml`, assign `LOCALIZED` or `DATA_READY`, create cases, or
construct dual chains.

## Round 2B: Post-Download Completion Boundary

Round 2B processes one approved bundle per assignment and starts only after
Round 2A completes. Its unit is one row from
`registry/localization_queue.jsonl` whose transfer targets all resolve under
that bundle's `artifacts/` directory.
The coordinator supplies `expected_target_paths` for the assignment by selecting
the acquisition-plan `target_path` values under the approved bundle target
prefix. Entries remain NAS-data-root-relative and are resolved against the
assignment's absolute `nas_data_root`. This list verifies only that the expected
physical files are present;
it is not a persistent `resource_ref` to TSV-row mapping and does not create a
coverage sidecar.

Round 2B may perform only bundle-level structural localization:

- verify downloaded artifact paths, regular-file status, sizes, and SHA-256
  hashes;
- extract archives into the same bundle's `extracted/` directory when
  extraction is necessary to enumerate or inspect approved resources;
- record archive members;
- inspect H5/H5AD keys and dimensions, `obs` and `var` columns, coordinate
  columns and coordinate ranges, image dimensions, sample identifiers, metadata
  columns, and equivalent file-format structure needed to establish local
  readability;
- record format, path, hash, and basic structural summaries for downloaded and
  extracted objects.

Before materializing an archive member, enumerate and normalize the complete
member table without extraction. Reject absolute member paths, `..` traversal,
paths escaping the assigned `extracted/` root, normalized-path collisions,
symbolic or hard links, and device, FIFO, socket, or other special-file
entries. Extract only regular files and directories into a fresh per-attempt
location under the assigned bundle, then verify and record the resulting paths,
sizes, and hashes before publication. Never overwrite an existing extracted
object in place. An unsafe archive or a local extraction defect is a
nonterminal validation failure requiring repair or redispatch; it is not by
itself evidence of external inaccessibility.

Round 2B must not perform clustering, differential expression, enrichment,
spatial statistics, reannotation, format conversion, biological interpretation,
or paper-result reproduction. It must not reconstruct approved-resource
coverage from the two-column TSV, create case IDs, assign `DATA_READY`, write
HVUs, or create dual-chain output. Bundle membership comes from the approved
queue row and the bundle-owned target directory, not from re-auditing
`registry/acquisition_plan.tsv`.

Each assignment must specify an existing host conda environment or conda prefix
for format readers. The worker may activate or call that environment but must
not install packages, create environments, modify environment state, or use an
unstated fallback environment.

Round 2B writes only necessary `extracted/` content inside the assigned bundle
and a bundle-owned `localization.yaml`, published last. If the assigned
existing conda environment cannot read the format, the worker returns the
nonterminal `worker_status: awaiting_environment`, publishes no
`localization.yaml`, and waits for the coordinator to retry with another
already existing environment. It does not write registry files, entity
manifests, case manifests, source manifests, data manifests, task packages,
HVUs, or chain artifacts.

The bundle terminal status is `LOCALIZED | BLOCKED_EXTERNAL`:

- `LOCALIZED`: every expected target path is present, hash-recorded, and
  structurally readable to the limited extent required above; required
  extraction has completed; `remaining_issue` is null.
- `BLOCKED_EXTERNAL`: one or more approved transfer objects are unavailable,
  corrupt, require external access or credentials, depend on an unavailable
  service, refer to an unrecoverable remote object, or are otherwise impossible
  to localize after retryable local causes have been exhausted. `remaining_issue`
  records the concrete unresolved condition.

Round 2B does not determine scientific usability, sample-object linkage,
article-supported scope, case admission, or `DATA_READY`.

## Coordinator Completion

The coordinator redispatches missing and retryable work until every expected
Round 1 entity has a terminal manifest, the filtered approved localization
queue has been published, and the complete acquisition plan has been
materialized. After Round 2A, it also redispatches Round 2B until every approved
bundle has a terminal `localization.yaml`. It does not create batch audit or
status-summary artifacts and does not return while actionable Round 1,
resource-selection, acquisition-plan, download, or Round 2B bundle-validation
work remains.

Round 1 completion for stages after the effective-intake amendment requires
terminal accounting for the paper, dataset, and linkage-edge counts declared by
the effective intake manifest. Every paper row and every linked STDS row must
satisfy the current-generation contract. Resource-selection completion requires
dataset and paper selection-manifest counts equal to the effective intake
counts, exact resource-decision coverage for every inventory row, no unresolved
review row, a validated approved queue, and a complete two-column acquisition
plan. Round 2A never starts automatically. Round 3 must not start until all
approved bundles have reached a Round 2B terminal state.

Logical atomic publication is mandatory:

1. A worker writes one generation under entity-specific staging.
2. The worker validates all files and returns the staged generation to the
   coordinator.
3. The coordinator holds the applicable publish lock.
4. The coordinator publishes companion files and atomically renames the manifest
   last.
5. Entity manifests use `generation_id` and `companion_records` checksums, and
   `resource_selection.yaml` records the selection generation and inventory
   checksum.
6. Readers accept only packages whose generation and recorded checksums match;
   they reject missing, mixed, or checksum-mismatched generations.
7. Staging and superseded files may be removed only after successful
   publication and a cleanup receipt inventories each exact target path, size,
   and SHA-256, proves any required canonical replacement, and confirms that no
   retained package references the target.

Any post-publication metadata or schema correction is an allowlisted,
coordinator-owned repair transaction rather than an in-place edit. A dry-run
proposal records exact precondition hashes and proposed outputs. After taking
the applicable locks, the coordinator rechecks those preconditions, stages and
validates the complete replacement set, and commits atomically with recoverable
`PREPARED`, `COMMITTED`, or `ROLLED_BACK` state and hashed backups. A repair
must not silently change scientific scope, resource identity, bundle membership,
or representation. Every downstream dispatch bound to changed bytes is marked
superseded and receives a new immutable generation and context before reuse.

For article generations, coordinator validation includes the PDF signature,
page count, text extraction, identity evidence, schema, checksums, linked-STDS
coverage, regular-file status, and byte identity between the canonical paper PDF
and every dataset-local materialization. A symlink fails publication. A failed
validation is repaired or redispatched and does not reduce worker-pool capacity.

The coordinator is the sole writer of registry files. Workers return proposed
records to the coordinator and cannot publish a partially valid package as
terminal. Completion requires no incomplete staging files, no missing terminal
manifests, and an empty transient review queue. Only the latest canonical entity
and bundle records remain published.

## Deferred Semantic Handoff

After Round 2B terminal localization, Round 3 evaluates one dataset-local
article and its STDS dataset case by case. It enumerates article Results,
filters by explicit use of the assigned spatial data, inspects only relevant
canonical data, identifies necessary auxiliary resources without downloading
them, and constructs supported candidates. A Round 2B terminal state is
transport evidence and does not establish scientific support, irrelevance, or
case admission. Round 3 is defined in [STOmicsDB Case Construction
Workflow](stomicsdb-case-construction-workflow.md).

When an operator later authorizes localization of retained Round 3 auxiliary
resources, one recoverable `round3_auxiliary_localization_binding` transaction
owns both package first-publication and complete case-tree replacement. Bind
each resource to its immutable acquisition inventory and successful run and
stage every immutable package generation under
`auxiliary_resources/<package_id>/generations/<generation_id>/`. Download
staging paths remain evidence only. Materialize artifact bytes before each
manifest by byte-stream copy or verified reflink, serialize `localization.yaml`
last, and validate all declared regular-file, readability, containment, size,
hash, acquisition, identity, and count facts. Stage and validate every complete
three-file case replacement before canonical mutation. Do not use a
metadata-preserving tree copy or hardlink to mutable download staging. Retain
the download inventory, run events, and source objects.

With the complete package and case lock set held and all preconditions
rechecked, publish and reopen every absent package generation first. Only after
all packages validate may the same transaction replace cases. Each localized
`Axx` binds one immutable package manifest and the exact nonempty artifact
subset covering all of its expected content. Resource identity and access
evidence, scientific `Rxx`, `Dxx`, and `Cxx`, and all non-target case fields
remain fixed. After every case replacement validates, mark prior chains bound
to replaced case bytes stale. Record `COMMITTED` only after package publication,
case replacement, and stale-chain handling all succeed.

Any later failure restores every replaced case from its hashed backup and then
deletes only package generations created by this transaction that no restored
or current case references. Validate the restored cases and absence of current
references to deleted generations before recording `ROLLED_BACK`; partial state
is not a valid terminal. Package publication and case adoption are never
reported as two distinct transactions.

Only a current case whose referenced `Dxx` and localized `Axx` bindings all
validate may be derived as `DATA_READY`. Source URLs, download completion,
staging artifacts, or unbound canonical packages are insufficient.

Stage 4 processing, including HVU definition, dual-chain construction, task
admission, hidden references, and benchmark evaluation, remains deferred. No
Round 1, Round 1.5, Round 2A, or Round 2B outcome predetermines those later
decisions.

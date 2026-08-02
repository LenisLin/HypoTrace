# STOmicsDB Dual-Chain Workflow

This workflow converts one accepted STOmicsDB Round 3 candidate into one
case-derived dual chain. Round 3 remains authoritative for candidate admission;
this workflow does not rediscover candidates and has no `no_candidate` outcome.

The operational path is intentionally small:

`Prepare -> Extract -> Validate -> Review -> Limited Repair -> Close`

The shared scientific and execution representation remains defined by
`docs/datasets/dual-chain-extraction.md`. The candidate worker contract is
`contracts/prompts/curation/stomicsdb/dual_chain/candidate_job.md`, and the
bounded multi-candidate dispatch contract is
`contracts/prompts/curation/stomicsdb/dual_chain/implementation_window.md`. The
machine-readable local schemas are:

- `contracts/schemas/stomicsdb_dual_chain_job.schema.json`;
- `contracts/schemas/stomicsdb_dual_chain_job_response.schema.json`;
- `contracts/schemas/stomicsdb_dual_chain_manifest.schema.json`;
- `contracts/schemas/scientific_chain.schema.json`;
- `contracts/schemas/execution_subchains.schema.json`.

## Unit of Work

One job owns exactly one `stds_id`, one Round 3 `candidate_id`, and the
deterministic chain ID:

```text
case_id = "stomicsdb_" + stds_id
chain_id = "chain_sha256_" + sha256(case_id + "\n" + candidate_id)[:16]
```

The complete job assignment must be present in the worker message. A path to
an assignment file is not task transport. The assignment binds the three
Round 3 manifests, initial extraction and review staging locations, final chain
location, current chain state, next action, and remaining revision budget. The
single-job `preflight-job` command validates it before role dispatch.

## 1. Prepare

Preparation is a lightweight preflight, not a new scientific audit. It checks
only facts that can change the decision to run extraction:

1. The three bound manifests exist, parse, match `stds_id`, and match their
   raw-byte SHA-256 bindings.
2. The selected candidate exists and its Rxx, Dxx, Axx, sample, component, and
   connection references resolve within the Round 3 case.
3. Required Dxx components and localized Axx artifacts are readable and match
   their existing path/hash/generation bindings. An absent Axx retains its exact
   external identity and limitation rather than being treated as a local file.
4. The deterministic chain identity and assigned NAS paths are canonical.

Hashes are computed at this validator boundary with an in-process cache. Do
not create checksum sidecars or ask extractor and reviewer roles to recompute
the same large-file hashes independently.

An absent, unreadable, or hash-mismatched article or Dxx closes the job as
`blocked`. When the only unresolved inputs are case-declared Axx resources with
`local_availability: absent`, preparation instead assigns their exact Dxx/Axx
boundary and proceeds to Codex extraction with `BLOCKED_EXTERNAL`. An execution,
transport, filesystem, or schema-call failure closes as `failed`. None of these
conditions is a scientific exclusion.

## 2. Extract

Extraction reads only the selected candidate, its declared source anchors, and
its exact Dxx/Axx input boundary. It writes exactly three nonempty files into a
unique NAS extraction-attempt staging directory:

```text
chain_manifest.yaml
scientific_chain.jsonl
execution_subchains.jsonl
```

Construct one S00 framing row and `1..n` aligned Sxx/Exx pairs. Hypotheses are
neutral questions or analysis targets. Direction, magnitude, significance,
null findings, and interpretation belong in result and conclusion fields.
Claims must remain proportional to the source evidence and study design.

Use source text, figure/table legends, labels, and reported values before image
interpretation. Inspect a retained figure only when the textual evidence does
not fully specify the bounded observation. Image reading may recover directly
visible labels, scale bars, counts, regions, or relative distributions; it
must not add significance, mechanism, causality, or biological identity absent
from the source.

## 3. Validate

The coordinator performs one strong validation pass over the staged output:

- exact file set and nonempty files;
- chain-manifest schema and three-manifest identity/hash binding;
- shared JSONL schemas and sequential Sxx/Exx identifiers;
- Sxx/Exx links and aligned observation bridges;
- execution input/output object continuity;
- Dxx/Axx boundary, exact component subsets, and wrapper references;
- exact preservation of unresolved Axx identity and access metadata without a
  fabricated localization binding;
- exact ordered Rxx-to-Sxx/Exx coverage and source-locator containment;
- no placeholders or unresolved cross-file references.

Schema-valid output is necessary but not sufficient for scientific
confirmation. Neutral-hypothesis and bounded-conclusion judgments belong to the
independent reviewer. The coordinator publishes a valid initial draft by same-NAS
atomic rename, then sends it to review.

## 4. Review

One targeted independent-curator review checks the drafted chain against the bound
Round 3 evidence. It does not repeat article discovery, auxiliary-resource
discovery, or data localization. Review produces only a proposed full
`chain_manifest.yaml` and `independent_check.md` in review staging; the
coordinator validates and publishes them through the existing locked,
recoverable transaction.

Review outcomes are:

- `confirmed`: the chain becomes `comparison_ready` when `DATA_READY`, or
  `specification_ready` when only exact absent-Axx dependencies remain;
- `needs_revision`: the evidence is available but the chain representation has
  a correctable problem;
- `blocked`: a physical article/Dxx failure is returned to the
  candidate controller and is not published as a reviewed chain state.

`needs_revision` declares `revision_scope: extraction | round3_handoff`.
Handoff findings close at the Round 3 boundary; only extraction findings enter
repair. Reviewers consume coordinator-validated immutable Dxx/Axx bindings and
do not independently rehash large artifacts.

## 5. Limited Repair

Repair is finding-directed. A revision receives the complete current
assignment, current chain, and the review's concrete revision findings. It may
change only the three extraction files needed to resolve those findings. Each
revision is validated, atomically replaces the reviewed draft through the
coordinator transaction, resets review to `not_started`, and receives one new
targeted review.

Allow at most two committed extraction revisions after the initial extraction.
Do not rerun an unchanged attempt, broaden the candidate, invent source
content, or use a favorable biological outcome as a repair criterion.

The revision budget is chain-lifetime, not job-local. Initial round paths come
from the assignment; later attempt components are deterministically
`<job_attempt_id>.r1` and `.r2`. Operation and transaction IDs are
`<job_attempt_id>.<phase>.r<round>`.

If an internally contradictory Round 3 handoff cannot support any valid Sxx/Exx
pair, close the job as `round3_handoff_needs_revision` and leave Round 3 as the
owning correction boundary. This job status is not a `chain_status` value and
does not authorize downstream scientific invention.

## 6. Close

The candidate job closes with exactly one status:

- `comparison_ready`: confirmed final directory contains exactly four files;
- `specification_ready`: confirmed final directory contains exactly four files,
  while `data_readiness` remains `BLOCKED_EXTERNAL` for exact unresolved Axx;
- `blocked`: required evidence or input cannot be validated;
- `round3_handoff_needs_revision`: the admitted candidate contract is
  internally contradictory;
- `failed`: execution, transport, filesystem, or validator operation failed.

`needs_revision` is an intermediate repair state, not a closed job. Exhausting
the two-revision limit closes as `failed` with the unresolved review findings;
it must not be relabeled as a scientific blocker.

## Runtime Records

The candidate controller and response validator are implemented. The following
batch records are reserved for a later batch controller; they are not implied
to exist for a single-job invocation:

```text
<batch_id>/
  assignment.yaml
  jobs/<job_attempt_id>/started.yaml
  jobs/<job_attempt_id>/terminal.yaml
  receipt.yaml
```

Do not add working-note ledgers, environment snapshots, duplicate hash files,
agent receipts, or step-by-step audit logs. Runtime records and chain outputs
belong under the declared STOmicsDB NAS staging/publication roots, never in Git.

## Publication and Recovery

The extractor and reviewer never write the final chain directory. The
coordinator owns locks, exact-file validation, same-filesystem atomic rename,
review/revision replacement transactions, and recovery. A failed operation may
clean only its own current staging directory. It must not edit or replace a
previously published chain outside the coordinator transaction.

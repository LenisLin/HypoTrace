# Dual Chain Extraction

## Purpose

Dual-chain records have two distinct uses in HypoTrace:

1. `agent-submitted dual chain`: an agent-facing output constraint for benchmark
   submissions.
2. `case-derived dual chain`: an evaluator-facing curation artifact extracted
   from screened papers, tutorials, or examples.

Both uses share the same core scientific-chain and execution-subchain schema.
They differ in provenance, visibility, and required execution granularity. The
case-derived chain is not a ground-truth trajectory and must not be exposed as
agent input.

## Core Principle

Use a shared core schema with different wrappers.

Agent-submitted chain:

- is submitted by the agent during a benchmark run
- must represent the agent's actual execution
- should contain real, checkable code paths, parameters, artifacts, and outputs
- belongs under the run `submission/` directory

Case-derived chain:

- is extracted by a curator from a screened paper, tutorial, or example
- is evaluator-facing
- is a curation artifact, not ground truth
- starts after pre-chain localization has produced `source_manifest.yaml` and
  `case_data_manifest.yaml`
- requires selected localized sources to support the selected execution
  granularity and case data localization to be `DATA_READY`
- uses either `source_analysis_granularity` or
  `concrete_execution_granularity`
- is insufficient if it only restates narrative paper text

## Shared Core Files

Both chain types strictly reuse the core JSONL files:

- `contracts/output_template/scientific_chain.jsonl`
- `contracts/output_template/execution_subchains.jsonl`

Do not add case-specific provenance, visibility, source-section, or extraction
status fields to the JSONL rows. Store those wrapper fields in
`chain_manifest.yaml`.

## Case-Derived Chain Files

Set `case_route: tool_method | public_database_stomicsdb`. The existing
tool/method route keeps the same method/case structure, with one directory per
extracted scientific chain:

```text
raw_data/tool_method/<method_slug>/
  screen/
    screening.yaml
  cases/
    <case_id>/
      case_screen.yaml
      source_manifest.yaml
      data/
        case_data_manifest.yaml
      dual_chain/
        <chain_id>/
          chain_manifest.yaml
          scientific_chain.jsonl
          execution_subchains.jsonl
          independent_check.md
```

The public-data STOmicsDB route uses the published public case directly:

```text
raw_data/public_database/stomicsdb/cases/<case_id>/
  case_manifest.yaml
  source_manifest.yaml
  data/case_data_manifest.yaml
  dual_chain/
    <chain_id>/
      chain_manifest.yaml
      scientific_chain.jsonl
      execution_subchains.jsonl
      independent_check.md
```

Its lightweight operational lifecycle, bounded repair loop, and terminal job
statuses are defined in `docs/datasets/stomicsdb-dual-chain-workflow.md`. This
document remains the shared scientific/execution representation authority.

For `case_route: public_database_stomicsdb`, one dispatch receives `stds_id`,
one `candidate_id`, absolute paths to the three Round 3 manifests, and one
target chain directory. Derive `case_id` as `stomicsdb_<STDS_ID>`. The route
does not require `method_slug`, `screening.yaml`, or `case_screen.yaml`. The
selected candidate is one complete chain scope and yields one chain directory
containing `1..n` HVU/E pairs. Do not broaden the candidate or infer missing
connections.

Compute the public-data `chain_id` deterministically as
`chain_sha256_<first 16 lowercase hexadecimal characters>` over the UTF-8 bytes
of `case_id + "\n" + candidate_id`, with no trailing newline. One tuple maps to
exactly one chain directory.

Absolute manifest paths are dispatch inputs only. Persist their
NAS-data-root-relative forms in `chain_manifest.yaml:input_binding` and hash the
exact raw bytes at each resolved path. These hashes are computed by the
dual-chain consumer and are not Round 3 fields.

For `case_route: tool_method`, the case-level `source_manifest.yaml` is consumed from
`raw_data/tool_method/<method_slug>/cases/<case_id>/source_manifest.yaml`.
`chain_manifest.yaml:source_manifest` stores that data-root-relative path, not
a copied manifest under the chain directory.

For the same route, method-level `screening.yaml` is consumed from
`raw_data/tool_method/<method_slug>/screen/screening.yaml`.
The case-specific screen slice is consumed from
`raw_data/tool_method/<method_slug>/cases/<case_id>/case_screen.yaml`. The case
data manifest is consumed from
`raw_data/tool_method/<method_slug>/cases/<case_id>/data/case_data_manifest.yaml`.
Downstream stages use method-level `screening.yaml` to confirm method/case
membership and use `case_screen.yaml` as the case-specific context. The case
screen provides data-access leads; it is not evidence for a scientific chain.
Case-derived tool/method extraction starts after pre-chain localization. It
consumes method-level `screening.yaml`, `method_slug`, `case_id`,
`case_screen.yaml`, `source_manifest.yaml`, and `case_data_manifest.yaml`. Chain
JSONL files are created only when localized source material can support at
least one HVU/E pair and
`case_data_manifest.yaml:case_data_manifest.data_localization_status` is
`DATA_READY`.

For `case_route: public_database_stomicsdb`, resolve the candidate through
`result_ids` and `result_order`. Build `S00` only from referenced
`data_context` records. Use `analysis_steps` as the source-supported
input/method/output skeleton, `result_connections` for cross-result continuity,
and `result_data_links[].data_inputs` to resolve `Dxx` inputs by
`input_role`, `sample_ids`, and `required_components`; resolve `Axx` through
`auxiliary_resource_ids`. `used_data_objects[]` is reserved for these `Dxx`
objects. Record a required localized `Axx` separately in
`used_auxiliary_resources[]` and bind it to its canonical package ID,
localization package generation, and exact artifacts. Eligible local IDs are the union of
`data_inputs[].data_id` for the candidate's results. Every member result must
declare the same nonempty `primary_spatial` set, and candidate
`spatial_data_ids` must equal that common set exactly. Record each used local
object by its Round 3 `data_id`. Reopen only `article_path` at the declared
`result_section` and `source_anchors` figure, table, or stable text locators,
and reopen only exact required component paths after confirming that each path
is a hash-valid subset of the referenced `Dxx` component files. Do not require
legacy source locators, mapping IDs, route segments, discovery snapshots, or
unrelated article/data discovery.
At minimum the route must support `source_analysis_granularity`. Select
`concrete_execution_granularity` only when canonical source material contains
source-observed code, calls, parameters, paths, or workspace objects.
If the selected candidate has missing or contradictory result/data references,
report the candidate job as `round3_handoff_needs_revision`; do not invent a
chain. `needs_revision` remains the intermediate chain/review state for a
correctable drafted representation.
Source-supported null or
non-significant observations are valid, and absent code is not a failure when
`source_analysis_granularity` is valid.

Round 3 candidate admission support and execution availability are separate.
Public-data `DATA_READY` in the downstream chain manifest is derived, not
copied. It requires every eligible `Dxx` root and every exact component path in
the selected results' `required_components` to be declared, readable, and
hash-valid. Optional or inapplicable components may be null. A required `Axx`
with `local_availability: absent` prevents `DATA_READY`, regardless of how well
its external access has been characterized. For `public_database_stomicsdb`, it
does not prevent Codex from extracting and independently reviewing a scientific
specification when all article and Dxx inputs validate; the reviewed final is
`specification_ready` and remains `BLOCKED_EXTERNAL`. A required `Axx` is localized only
when its case record has `local_availability: localized`, a
non-null `localization_binding` whose package manifest path, raw-byte SHA-256,
`package_id`, and `generation_id` resolve to a
canonical auxiliary-resource manifest with
`auxiliary_localization_manifest.localization_status: LOCALIZED`. The case
binding and canonical manifest must agree on resource identity, package and
generation IDs, and every required artifact path and SHA-256. All selected
requirements must be covered by the case
`Axx.localization_binding.expected_content_coverage`, every cited artifact ID
must resolve in the canonical manifest, and no uncovered required item is
allowed. A URL,
download event, staging artifact, or access characterization alone is not a
localized input.

One tool/method screened case may produce zero, one, or multiple
`dual_chain/<chain_id>/` directories. One public-data case produces one
directory per candidate selected for downstream extraction. Do
not create empty JSONL files until real extraction begins.

Operational split: tool/method extraction is scoped to one `method_slug`, one
`case_id`, and one target chain directory. Public-data extraction is scoped to
one `case_id`, one candidate ID, and its deterministic target chain
directory. A case with multiple independent candidates uses multiple
chain directories and dispatches. Chain-independent confirmation is scoped to
one existing chain directory and proposes only that chain's review outputs
through the atomic review workflow below.
Independent-check status and summary findings remain recorded in
`chain_manifest.yaml:independent_check`; detailed checklist findings live in
`independent_check.md`.

Every public STOmics queue row and fully instantiated Stage 3 or Stage 4
assignment carries `stds_id`, `candidate_id`, absolute paths to
`case_manifest.yaml`, `source_manifest.yaml`, and
`data/case_data_manifest.yaml`, the deterministic `chain_id`, and unique
absolute extraction staging, review staging, and final chain paths. A durable
queue or assignment file is a binding record, not child-task transport; the
child message contains the complete assignment.

### Atomic Stage 3 Publication

The coordinator assigns one unique NAS attempt staging directory, an absent
final chain directory, and a chain-specific lock for every extraction attempt.
The curator writes exactly these three nonempty files directly in attempt
staging and never writes the final directory:

- `chain_manifest.yaml`
- `scientific_chain.jsonl`
- `execution_subchains.jsonl`

After the curator returns, the coordinator acquires the chain lock, confirms
the final directory is still absent, and validates the complete cross-file
contract. This includes route and identity fields, deterministic `chain_id`,
input manifest paths and raw-byte hashes, data and auxiliary bindings, all Sxx/E
references, JSONL parsing and schemas, and the requirement that both JSONL files
contain records. Only then does the coordinator atomically rename the attempt
directory to the final directory on the same NAS filesystem. Validation or
rename failure leaves no partial final tree; only the current attempt staging
may be cleaned. Never publish empty JSONL placeholders.

### Atomic Stage 4 Review And Replacement

The independent reviewer receives a unique NAS review staging directory. The
reviewer writes only a proposed full `chain_manifest.yaml` and
`independent_check.md` there; both are nonempty and no other file is written.
The reviewer never writes the final chain directory. The
proposal must bind the current final manifest and both JSONL raw-byte hashes.
The coordinator then acquires the chain lock, reopens the final and proposed
files under that lock, and verifies that the final JSONL files are
byte-unchanged, that the proposed manifest changes only fields allowed by Stage
4, and that the review file and manifest status agree.

Without releasing the lock, publication uses a recoverable per-chain
replacement transaction. The transaction records `PREPARED`, places the current final
`chain_manifest.yaml` and `independent_check.md` when present in a unique NAS
backup, installs the validated proposed files, verifies the resulting final
tree and unchanged JSONL hashes, and then records `COMMITTED`. Any failure after
preparation restores the backup, verifies restoration, and records
`ROLLED_BACK`. Historical transaction and backup records are retained.

A Stage 4 `needs_revision` decision does not authorize the reviewer to edit
JSONL. A later extraction replacement uses a new attempt staging directory and
the same locked, recoverable replacement pattern with a backup of the complete
prior chain. The replacement is validated as a complete three-file Stage 3
product and resets `independent_check.status: not_started`; it does not combine
old and new JSONL rows or revise JSONL in review staging.

A chain becomes `comparison_ready` only when:

- the route-appropriate status is `DATA_READY`: copied from
  `case_data_manifest.data_localization_status` for `tool_method`, or derived
  from referenced `Dxx` and `Axx` records for `public_database_stomicsdb`;
- `chain_manifest.used_data_objects[]` resolves to localized data records;
- every required `chain_manifest.used_auxiliary_resources[]` entry validates
  against its selected localized `Axx` and a canonical `LOCALIZED` package;
- chain JSONL follows the shared contract;
- result observations are supported by localized source material or localized
  data records;
- `independent_check.status` is `confirmed`.

A STOmics chain becomes `specification_ready` when the same extraction,
structural validation, source support, and independent confirmation pass, but
the only unresolved inputs are exact case-declared Axx resources with
`local_availability: absent`. Their wrappers preserve resource identity,
expected content, source URL, access classification, and access notes without
inventing localization. `specification_ready` is not `DATA_READY` and does not
authorize execution.

## Curator Construction Workflow

Case-derived chains should be constructed in this order. Steps 1-2 apply only
to `case_route: tool_method`; for `public_database_stomicsdb`, first bind and
validate the three manifests and selected candidate instead. Derive S00 from
referenced data contexts. Construct the chain only from the selected
candidate's ordered results. For each result, reread the assigned dataset-local
article at its Results section and declared `source_anchors`, use its ordered
analysis steps, and resolve exact inputs through
`result_data_links[].data_inputs[].required_components`. Do not broaden the
candidate or infer missing connections.

1. Read method-level `screening.yaml` to confirm method/case membership.
2. Read per-case `case_screen.yaml` as case context.
3. Read per-case `source_manifest.yaml` for localized source material.
4. Read per-case `case_data_manifest.yaml`. For `tool_method`, require
   `data_localization_status: DATA_READY`; for
   `public_database_stomicsdb`, derive readiness from all selected `Dxx` and
   canonically bound `Axx` inputs; retain exact absent-Axx requirements as
   external wrappers.
5. Stop before creating JSONL files when localized source material or required
   Dxx is incomplete. A STOmics candidate whose only unresolved inputs are
   absent Axx proceeds as a `BLOCKED_EXTERNAL` scientific specification.
6. Draft one chain scope in `chain_manifest.yaml`: scientific objective, data context, and dependency summary.
7. Select `source_analysis_granularity` or `concrete_execution_granularity`.
8. Write `S00` from source screening and localized data summaries for
   `tool_method`; for `public_database_stomicsdb`, derive it only from the bound
   case, source, and data manifests.
   When no selected auxiliary input contributes samples, a non-null
   `sample_count` equals the selected Dxx sample-ID count. When a canonically
   localized Axx contributes additional samples, `sample_count` may describe
   the full Dxx+Axx scope only when the bound manifests support that total; it
   must not be smaller than the Dxx count. Use `null` when the full-scope total
   is unresolved.
9. Draft HVU candidates from localized source and data material.
10. Run the internal HVU candidate check before assigning final Sxx identifiers.
11. Revise candidates until each remaining unit has one scientific target, a
    neutral hypothesis target, minimum result material, one
    result-to-conclusion progression, and a linked execution route.
12. Assign final Sxx identifiers only to checked candidates.
13. For each final HVU, write `hypothesis` as a neutral scientific or analysis
    target, then `experiment.summary`.
14. Use neutral verbs such as Evaluate, Compare, Assess, Estimate, or
    Characterize. Put observed direction, values, named regions, marker
    patterns, null results, and interpretation in result/conclusion fields.
15. Draft the linked primary execution subchain for the HVU.
16. Run the execution route and subchain check before accepting the HVU/E pair.
17. Fill `result.observations[]` from result-bearing outputs or source result locators aligned with the execution route.
18. Write `conclusion.summary` and `next_hypothesis` only after the HVU result and execution bridge are consistent.
19. Record claimed source materials, `Dxx` data objects, and separately wrapped
    `Axx` auxiliary inputs in `chain_manifest.yaml`.
20. Leave object resolution, source-support confirmation, schema checks, and status updates to the chain-independent confirmation stage.

## Chain-Independent Confirmation

Chain-independent confirmation is a lightweight post-extraction checklist
workflow. One invocation reviews one existing chain directory.

For `public_database_stomicsdb`, confirmation performs this lightweight Round 3
handoff check in addition to the shared JSONL and chain checks. It does not
repeat Round 3 article, resource, or canonical-data discovery:

1. The three manifests parse and have the assigned `stds_id`.
2. The selected `candidate_id` exists.
3. Every `result_id`, `Dxx`, and `Axx` reference resolves; each
   `used_data_objects[].id` equals a Round 3 `data_objects[].data_id` in the
   candidate results' `data_inputs`, every required component path is a
   hash-valid subset of that `Dxx` component's files, and every member result's
   common `primary_spatial` set equals `spatial_data_ids`.
   `used_data_objects[]` is `Dxx`-only; every used `Axx` resolves through
   `used_auxiliary_resources[]`.
4. `result_order` contains exactly the candidate result set without duplicates.
5. Every connection references candidate results and its `from_output` and
   `to_input` values match the corresponding analysis steps.
6. Every connected result uses the candidate's same primary logical spatial
   `Dxx` and every connection matches the declared route.
7. S00 uses only referenced data contexts.
8. Each HVU/E pair is supported by the selected result's `source_anchors` and
   analysis steps.
9. Required `Dxx` roots and exact component paths are readable and hash-valid.
10. External `Axx` inputs retain their actual access limitation; any required
    `local_availability: absent` resource prevents `DATA_READY` but may remain in
    a reviewed `specification_ready` wrapper. Every localized
    `Axx` passes the canonical package identity, manifest path/hash,
    package/generation, artifact path/hash, and expected-content coverage checks.

1. For `tool_method`, read method-level `screening.yaml` and per-case
   `case_screen.yaml`; for `public_database_stomicsdb`, verify the manifest
   input binding and selected candidate.
2. Read per-case `source_manifest.yaml` and localized source material.
3. Read per-case `case_data_manifest.yaml`. For `tool_method`, require
   `data_localization_status: DATA_READY`; for `public_database_stomicsdb`,
   derive readiness from exact required component paths. An absent Axx may be
   confirmed only as an exact external wrapper leading to
   `specification_ready`; it never leads to `comparison_ready`.
4. Read `chain_manifest.yaml`, `scientific_chain.jsonl`, and
   `execution_subchains.jsonl`.
5. Parse every non-empty JSONL line and validate each record against
   `contracts/schemas/scientific_chain.schema.json` or
   `contracts/schemas/execution_subchains.schema.json`, as appropriate. Record
   a parse or schema failure as `needs_revision`; schema failure alone is not
   `blocked` when the underlying source and localized data remain available.
6. Write a proposed complete `chain_manifest.yaml` and `independent_check.md`
   only in the coordinator-provided review staging directory. Include checklist
   findings for case membership,
   data readiness, source traceability, scientific chain structure, HVU
   granularity, primary result material, execution chain structure,
   execution-to-result alignment, data object consistency, and conclusion
   placement.
7. Record summary findings, `notes_location`, and final independent-check status
   in the proposed `chain_manifest.yaml:independent_check`.
8. Keep proposed `chain_manifest.yaml:chain_status` consistent with the confirmation
   outcome.
9. Leave `scientific_chain.jsonl` and `execution_subchains.jsonl` unchanged.
   Correctable extraction issues are recorded as revision findings.
10. Return review staging and the inspected final-file hashes. The reviewer
    never writes final; the coordinator validates and publishes through the
    locked recoverable Stage 4 transaction.

For case-derived chains, Stage 4 confirms source-extracted execution. It does
not run, replay, or regenerate the analysis. Source-observed calls, parameters,
assignments, returned objects, mutations, and save targets support the execution
route; scientific observations require separate source-retained result evidence.

For STOmics, scientific observation support is limited to declared article
anchors or a Round 3 result object explicitly bound as precomputed evidence.
A raw or input Dxx/Axx object establishes execution availability, not a new
scientific observation. Figure reading may recover directly visible labels,
scale bars, counts, regions, or relative distributions, but not unreported
significance, causality, mechanism, or biological identity.

Review result evidence from source text and figure/table annotations first,
then retained textual or structured outputs, and inspect retained images only when needed.
Source localization is judged for sufficiency to support the written
chain, not for completeness.

Stage 4 distinguishes unavailable confirmation evidence from correctable chain
representation. Missing required input data or primary source evidence is
`blocked`. Available evidence with incorrect granularity, linkage, locator,
object reference, or result placement is `needs_revision`.

The prompt template lives at
`contracts/prompts/curation/dual_chain_independent_check.md`.

## Scientific Chain Requirements

`scientific_chain.jsonl` contains one `S00` study-framing record and one or more HVU records.

For case-derived chains:

- `S00` records data type, organism, tissue, sample count, spatial unit count, sample structure, grouping variables, available metadata, and unresolved notes.
- `S00` does not record source conclusions, analysis scope, or QC results.
- each HVU contains `hypothesis`, `experiment`, `result`, `conclusion`, and `next_hypothesis`.
- `experiment.summary` records the scientific-level verification or analysis experiment.
- `experiment.execution_subchain_ids` is the scientific-to-execution link.
- `result.observations[]` records concrete source-supported or data-derived observations.
- each observation contains `observation`, `support`, and `interpretation`.
- `conclusion.summary` records the bounded interpretation across the result observations.
- publication or tutorial source type does not change the scientific-chain core shape.
- execution details remain in `execution_subchains.jsonl`.
- publication-derived chains are source anchors, not ground truth trajectories.

### Scientific Chain Boundary

Keep HVUs in the same scientific chain when downstream hypotheses use an
upstream result or object as an input, predictor, candidate set, score, region
definition, comparison basis, or evidence object. Examples include a
localization result followed by clinical association on the localized object, or
an SVG result followed by ligand-receptor analysis on the selected genes.

Split chains when the analysis object and the scientific question both change
and no upstream dependency is needed. Method type, figure or section, statistical
level, or dataset change alone is not a split criterion. A validation, replicate,
or cohort extension may remain in the same chain when it tests the same
scientific question and depends on the same upstream object or result.

### HVU Candidate Check Loop

Stage 3 first extracts draft HVU candidates. A draft candidate is not a final
HVU and does not receive an Sxx identifier. Before JSONL writing, apply the
candidate check loop:

1. Scientific target check: the candidate names the scientific or analysis
   result object being claimed.
2. Hypothesis target check: the candidate writes the hypothesis as a neutral
   analysis target. It names the object, dimension, comparison, relationship,
   or spatial context to evaluate, without stating the observed direction,
   existence, alignment, enrichment, significance, or tool success.
3. Minimum result check: the candidate has target object,
   relationship/pattern/context, primary result material, and support locator.
4. Single progression check: the candidate follows one hypothesis -> experiment
   -> result -> conclusion progression.
5. Support embedding check: input, reference, annotation, model object,
   plotting, and intermediate objects stay in execution or manifest context
   when they support another result target.
6. Conclusion closure check: conclusion.summary only synthesizes the
   candidate's own result observations.
7. Execution route check: the candidate has one supportable primary execution
   route. After final Sxx identifiers are assigned, write that route as the
   linked primary execution subchain.

Split a candidate when the assertion object, evidence type, statistical level
with verification target, claim strength, dependent downstream evidence, or
result-to-conclusion progression changes. Use these signals together; no single
signal is required to be sufficient by itself.

Candidate target selection workflow:

1. Name the candidate target object: the object the source case makes a claim
   about.
2. Classify supporting objects as input, reference, annotation, intermediate,
   or result-bearing objects.
3. Keep a candidate as a final HVU only when the source case gives the target
   object its own hypothesis, experiment, result, and conclusion progression.
4. Keep reference, annotation, and intermediate objects inside the linked
   execution route when they support another target object.

Do not split one HVU only because the same hypothesis uses multiple markers, features, plots, display formats, code cells, or intermediate output objects.

Multiple genes, markers, cell types, panels, or metrics may remain in one HVU
when they support the same target object and bounded claim.

Keep contrastive material in one HVU when both sides define one bounded metric
or comparison target. Split when the contrast contains separate result targets
with separate result-to-conclusion progressions.

The `result` field should describe the observation supported by the source or
curation process. The `conclusion` field should describe the bounded
interpretation and should distinguish association, co-localization, enrichment,
prediction, and causal interpretation.
Represent scope and limits in `conclusion.summary`,
`chain_manifest.yaml.limitations`, and final or evaluator layers, not as extra
scientific-chain core fields.

Stage 4 checks observation target alignment, hypothesis-result polarity, and
support-object placement. Stage 3 should revise final HVUs before JSONL writing
when a candidate mixes targets, pre-writes result direction into the hypothesis,
or places support/context objects into primary result observations.

### Minimum Result Material

Result and conclusion writing workflow:

1. Locate the HVU target object.
2. Extract observations using human-readable result language that names the
   target object, states the observed relationship or pattern, gives the
   tissue, region, layer, sample, or group context, and records a value,
   threshold, count, score, rank, marker, named qualitative pattern,
   source-stated direction, source-stated absence, non-detection, null result,
   or non-significant pattern when available.
3. Write `support` as the source locator or localized data object that supports
   the observation.
4. Write `interpretation` as the bounded meaning of that observation.
5. Write `conclusion.summary` as the bounded claim supported across the
   observations, using precise claim strength and no new facts.

Observation placement rule:

- Put result patterns, values, markers, regions, counts, scores, ranks,
  thresholds, or named qualitative patterns in scientific
  `result.observations[]`.
- Each final HVU must include at least one primary result observation:
  relationship, pattern, contrast, value, statistic, marker/region pattern, or
  explicit null/non-significant result. Object existence, table shape, column
  names, loaded files, metadata, and plotting availability are supporting
  material unless they are paired with a primary result observation.
- Put data loading, reference construction, model fitting, factor selection,
  object export, plotting parameters, and localization-readiness facts in the
  linked execution subchain, `chain_manifest.yaml` context, limitations, used
  data, or source entries, or `observation.support` as a source/data locator
  unless they are the result object being evaluated.

## Execution Chain Requirements

An execution chain is an ordered multi-step route serving one linked HVU. It
must explain how the linked HVU's result material is produced or supported.
Each non-framing HVU should have one primary execution subchain that covers the
full experiment-to-result route for that HVU. Additional execution
subchains are allowed only for independent verification routes, not for ordinary
intermediate steps or complementary evidence within the same route.

### Execution Route and Subchain Check

Apply this check after a candidate becomes a final HVU and before accepting the linked JSONL rows:

1. Link check: the subchain links to exactly one final non-S00 HVU and covers that HVU's experiment-to-result route.
2. Granularity check: use `concrete_execution_granularity` when localized source material provides code, notebook, script, path, variable, function, parameter, returned object, or saved output names; use `source_analysis_granularity` when the source only provides article-denoted analysis objects.
3. Step transition check: each step records a source-backed object transition in `inputs -> call(parameters) -> outputs` order.
4. Object continuity check: downstream inputs reuse the exact upstream output ID for the same logical object.
5. Source-backed call check: calls and key parameters come from localized source material or source-denoted analysis descriptions.
6. Result-bearing output check: the route reaches at least one output object, figure, table, or source result locator that can support the linked HVU result.
7. Result bridge check: `result_extraction.observations[]` aligns with the linked HVU `result.observations[]`.
8. Placement check: input structure, reference construction, model fitting, object export, plotting settings, and localization-readiness facts stay in steps, parameters, `source_ref`, `chain_manifest.yaml`, or locator support unless they are the result being evaluated.

If independent checking shows that an article-fixed result route does not use
the assigned primary spatial `Dxx`, do not represent that object as a
consumed-but-excluded execution input. This disproves the Round 3
`uses_assigned_spatial_data: yes` eligibility decision. Preserve the chain and
case as incident evidence, apply a new evidence-bound post-publication scope
transaction that removes the affected `Rxx` and candidate closure, and then
re-audit and re-extract any surviving candidates whose case-manifest hashes
changed.

An execution step is a source-backed operation that changes the state of an evidence object. Typical steps include loading source data, preparing or filtering an object, constructing a model input, fitting or running a model, exporting a result-bearing object, applying a statistical test, ranking or filtering results, and generating a figure or table used for result extraction.

Do not create separate steps for pure variable renaming, display styling, narrative interpretation, or code that does not create, transform, test, rank, or materialize an evidence object.

Each execution subchain must write one or more `steps[]` entries in method-call
order. Each step records object-level `inputs -> call(parameters) -> outputs`
and `source_ref`. Inputs and outputs use lightweight objects with `id`,
`object_content`, and `format`. `outputs` must contain at least one named result
object. `inputs` may be empty only for source-loading, object-creation, or
initialization steps without an upstream data object.

Use object IDs as logical object identifiers within one submission or case.
When a downstream step consumes a prior output, reuse the exact output object
ID. The same object ID must refer to the same logical object throughout the
chain; do not reuse one ID for different objects.

Full code is not embedded in `execution_subchains.jsonl`. Use `source_ref` to
record the local code, notebook, repository, script, documentation section,
figure, or table location supporting the step. Do not write only narrative
summaries such as "authors applied X."

`result_extraction.observations[]` records the observations extracted from the route. These observations should align with the linked HVU `result.observations[]`. Use the same `observation/support/interpretation` shape. Unknown parameters are not fabricated; record all source-observed key parameters in `parameters`.

### Execution Granularity

Select one execution granularity per chain and record it in
`chain_manifest.yaml`.

Stage 4 evaluates each chain against its declared execution granularity.
`source_analysis_granularity` does not require localized runtime-derived
artifacts when publication source locators directly support the reported result.
`concrete_execution_granularity` requires localized executable source and the
required input-to-result route. Neither mode requires rerunning the analysis
during independent confirmation.

`source_analysis_granularity` is a source-backed analytical route using
source-denoted objects. Inputs and outputs may be descriptive objects, such as
data objects, result tables, figure panels, reported clusters, gene sets,
regions, or analysis products named in the source. Each call must be a
source-backed method, function, model, test, or analysis operation.

`concrete_execution_granularity` is a code/workspace-backed route using
variables, files, commands, code blocks, or stable object IDs tied to executable
material. This is expected for tutorials, official examples, repositories,
notebooks, scripts, or article cases where executable source material is
available.

For `concrete_execution_granularity`, use source-observed object names from
localized code, notebooks, scripts, commands, file paths, variables, function
calls, parameters, returned objects, or saved outputs. When localized source
material only supports conceptual object descriptions, use
`source_analysis_granularity`.

Both granularities use the same
`inputs -> call(parameters) -> outputs -> result_extraction` structure and must
not reduce a source section to a narrative summary.

Use the strongest granularity supported by the localized sources. Do not choose
`concrete_execution_granularity` unless the localized source material ties the
route to source-observed code or workspace object names. Do not write unresolved
placeholders or inferred pseudo-objects into JSONL rows.

## `chain_manifest.yaml` Template

```yaml
case_id:
chain_id:
case_route: tool_method | public_database_stomicsdb
chain_origin: case_derived
input_binding:
  stds_id:
  candidate_id:
  case_manifest:
    path:
    sha256:
  source_manifest:
    path:
    sha256:
  case_data_manifest:
    path:
    sha256:
chain_status: draft | needs_revision | comparison_ready | specification_ready | blocked
chain_scope:
  scientific_objective:
  data_context:
  dependency_summary:
independent_check:
  status: not_started | confirmed | needs_revision | blocked
  reviewer_independence: independent_curator | self_review_with_limitation
  revision_scope: null | extraction | round3_handoff
  checked_sources:
    - source_id:
      local_path:
      source_role:
      locator:
  checked_data_objects:
    - id:
      role:
      local_or_prepared_path:
      artifact_refs:
        - name:
          role:
          path_or_locator:
      read_summary_used:
  checked_unresolved_auxiliary_resource_ids:
    - A01
  findings_summary:
    blocking:
      - "<blocking finding>"
    needs_revision:
      - "<revision finding>"
    notes:
      - "<note>"
  notes_location: dual_chain/<chain_id>/independent_check.md
source:
  route: bioinformatics_tool_paper | public_database_stomicsdb
  source_type: paper_case_section | official_tutorial
  tool:
  paper_or_doc:
  section_or_example:
  link:
  repository:

source_manifest:
case_data_manifest:
used_localized_sources:
  -
used_data_objects:
  - id: <case_data_manifest_data_object_id>
    role: <role>
    artifact_refs:
      - name: <internal_artifact_or_object_name>
        role: <artifact_role>
        path_or_locator: <data-root-relative-path-or-source-locator>
    required_by_scientific_units:
      - S01
    required_by_execution_subchains:
      - E01

used_auxiliary_resources:
  - id: <round3_auxiliary_resource_id_Axx>
    canonical_resource_id: <same-value-as-localized-package-id>
    package_id: <localized_package_id>
    role: <scientific_or_execution_input_role>
    localization_binding:
      package_manifest:
        package_id: <localized_package_id>
        path: <NAS-data-root-relative-canonical-manifest-path>
        sha256: <raw-byte-sha256>
        generation_id: <localization-generation-id>
    artifact_refs:
      - artifact_id: <canonical-artifact-id>
        path: <NAS-data-root-relative-artifact-path>
        sha256: <artifact-sha256>
    required_by_scientific_units:
      - S01
    required_by_execution_subchains:
      - E01

  # Alternative unresolved-Axx wrapper; do not add localization fields.
  - id: A02
    role: <scientific_or_execution_input_role>
    resource_name: <exact-case-declared-resource-name>
    expected_content: <exact-case-declared-expected-content>
    source_url: <exact-case-declared-source-url>
    access_classification: <exact-case-declared-access-classification>
    local_availability: absent
    access_notes: <exact-case-declared-access-notes>
    required_by_scientific_units:
      - S02
    required_by_execution_subchains:
      - E02

round3_result_bindings:
  - result_id: R01
    scientific_unit_ids:
      - S01
    execution_subchain_ids:
      - E01

data_readiness:
  status: DATA_READY | BLOCKED_EXTERNAL | not_checked
  required_data_objects_resolved: yes | no | not_checked
  unresolved_data_objects:
    -
  notes:

schema_check:
  scientific_chain_schema: contracts/output_template/scientific_chain.jsonl
  execution_subchain_schema: contracts/output_template/execution_subchains.jsonl
  jsonl_extension_policy: no_extra_fields

visibility:
  agent_visible: no
  evaluator_facing: yes
  hidden_reference_candidate: yes

extraction_policy:
  construction_mode: hvu_execution_alternating
  execution_route: ordered_multi_step_method_call_route
  result_material: concrete_numeric_or_biological_analysis_content
  scientific_unit_requirement: "Each non-framing HVU should have one primary execution subchain covering its experiment-to-result route."
  execution_granularity: source_analysis_granularity | concrete_execution_granularity
  minimum_execution_detail:
    - data object type
    - method or algorithm name
    - function name when available
    - key parameters when available
    - output object or reported result

provenance:
  source_sections:
    -
  source_notebooks_or_scripts:
    -
  source_figures_or_tables:
    -

limitations:
  -

scientific_cautions:
  - "Publication-derived chain is not ground truth."
  - "Do not force agents to reproduce the publication path."
  - "Separate computational observations from biological conclusions."
  - "Avoid causal, clinical, or mechanistic overclaims unless the study design supports them."
```

For `case_route: public_database_stomicsdb`, `input_binding` is mandatory and
all three manifest hashes must resolve; `source.tool` and tool/method screening
fields are null or omitted. A STOmics `comparison_ready` artifact records
`DATA_READY`, `required_data_objects_resolved: yes`, and no unresolved objects.
A `specification_ready` artifact instead records `BLOCKED_EXTERNAL`,
`required_data_objects_resolved: no`, and the exact absent Axx IDs. Physical
article or Dxx blocked state belongs to the job response and does not create a
chain artifact. For `case_route: tool_method`, the existing
screening/case-screen fields remain authoritative and the public-data-specific
candidate binding is not required. `used_data_objects[]` contains only `Dxx`
data objects. `used_auxiliary_resources[]` contains only `Axx` wrappers and is
required for each auxiliary input actually used by an Sxx or E. Every localized
wrapper must match the selected case `Axx.localization_binding` and the
raw-byte-bound canonical manifest. Its `canonical_resource_id` and `package_id`
must both equal the localized package's `package_id`; the nested
`package_manifest` fields must match
`auxiliary_localization_manifest.package_id` and `generation_id`; every
`artifact_ref` must resolve exactly to a canonical manifest artifact and be
an exact ID/path/hash projection of the selected
`Axx.localization_binding.artifacts`, and be covered by that Axx binding's
`expected_content_coverage`. Every unresolved wrapper must exactly preserve the
selected case Axx resource name, expected content, source URL, access
classification, access notes, and `local_availability: absent`, and must omit
package, artifact, local-path, and hash fields. The core JSONL schemas do not
change.

For new STOmics extraction and revision outputs,
`round3_result_bindings[].result_id` follows candidate `result_order` exactly;
each non-S00 Sxx and every Exx occurs in exactly one binding, and each bound Exx
links to an Sxx in the same binding. This field is optional only when reopening
an already confirmed legacy STOmics final that predates the field. STOmics
`comparison_ready` and `specification_ready` also require
`reviewer_independence: independent_curator`.

## Minimal JSONL Examples

These templates illustrate field roles and HVU/execution granularity. They serve
as schema examples rather than source-specific task answers. Placeholder markers
such as `<specific_target_object>`, `<observed_relationship_or_pattern>`,
`<reported_value_or_named_pattern>`, and `<source_ref_locator>` are replaced
with source-specific material before `comparison_ready`. If source-specific
material cannot be located, keep `chain_status` below `comparison_ready`. Use
reported integers when sample or spatial-unit counts are available; use `null`
when those counts are unresolved.

```jsonl
{"scientific_unit_id":"S00","parent_units":[],"data_summary":{"organism":"<organism>","tissue":"<tissue_or_context>","data_types":["<data_type>"],"sample_count":null,"spatial_unit_count":null,"sample_structure":["<sample_or_replicate_structure>"],"grouping_variables":["<group_or_condition>"],"metadata_available":["<metadata_field>"],"notes":["<screening_or_source_limit>"]}}
{"scientific_unit_id":"S01","parent_units":[],"hypothesis":"Evaluate <specific_target_object> with respect to <relationship_or_pattern_dimension> in <specific_context>.","experiment":{"summary":"<scientific_level_verification_or_analysis_experiment>.","execution_subchain_ids":["E01"]},"result":{"observations":[{"observation":"<specific_target_object> shows <observed_relationship_or_pattern> in <specific_context> with <reported_value_or_named_pattern>.","support":"<figure/table/notebook_output/local_object_locator>","interpretation":"This is <claim_strength> evidence within <case_limit>."}]},"conclusion":{"summary":"Within <case_limit>, the observations support a <claim_strength> claim that <specific_target_object> has <relationship> in <context>."},"next_hypothesis":"<next_source_supported_hypothesis_or_null>"}
```

```jsonl
{"execution_subchain_id":"E01","linked_scientific_unit_id":"S01","steps":[{"step_id":"E01.1","inputs":[{"id":"<raw_or_prepared_input_object_id>","object_content":"<source_named_input_object_content>","format":"<format>"}],"call":"<source_named_loader_or_preprocessing_call>","parameters":{"<known_parameter>":"<source_value>"},"outputs":[{"id":"<prepared_object_id>","object_content":"<prepared_object_content>","format":"<format>"}],"source_ref":{"type":"<source_ref_type>","locator":"<source_ref_locator>"}},{"step_id":"E01.2","inputs":[{"id":"<prepared_object_id>","object_content":"<prepared_object_content>","format":"<format>"}],"call":"<source_named_analysis_call>","parameters":{"<known_parameter>":"<source_value>"},"outputs":[{"id":"<specific_result_object_id>","object_content":"<object_containing_reported_value_or_named_pattern>","format":"<table_figure_or_object_format>"}],"source_ref":{"type":"<source_ref_type>","locator":"<source_ref_locator>"}}],"result_extraction":{"observations":[{"observation":"<specific_target_object> shows <observed_relationship_or_pattern> in <specific_context> with <reported_value_or_named_pattern>.","support":"<specific_result_object_id_or_source_locator>","interpretation":"This is <claim_strength> evidence within <case_limit>."}]}}
```

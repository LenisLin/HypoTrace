# Contracts

This directory stores HypoTrace contract assets: agent-facing output controls,
condition-specific input templates, prompt templates, config templates, task
registry templates, schema placeholders, and shared submission requirements.

## Layout

```text
contracts/
  HYPO_TRACE_SKILL.md
  output_template/
  checklists/
  submission_contract.yaml
  config_templates/
  task_registry_template/
  skills/
  prompts/
    task/
    curation/
  schemas/
```

`HYPO_TRACE_SKILL.md` and `output_template/` are the shared output contract for
all model-harness-conditions. Runner preparation may copy them into a sandbox as
`HYPO_TRACE_SKILL.md` and `output_template/`, but the repository source of truth
lives here.

The shared dual-chain output contract uses one `S00` study-framing row and HVU
rows with `hypothesis`, `experiment`, `result.observations[]`, `conclusion`, and
`next_hypothesis`. Execution subchains use ordered `steps[]` and
`result_extraction.observations[]`.

`skills/` contains condition-specific templates for B/C inputs. These templates
must not replace or modify the shared output contract.

`prompts/` contains reusable prompt templates. `prompts/task/` stores
agent-facing task prompt templates; these must not include hidden references,
scoring rubrics, or evaluator prompts. `prompts/curation/` stores internal
curator or evaluator-facing prompts and must not be copied into agent
workspaces.

Current curation prompts:

STOmicsDB public-database curation prompts:

- `prompts/curation/stomicsdb_round1_article_localization.md`: localize one
  DOI-deduplicated paper and linked STDS article packages for Round 1.
- `prompts/curation/stomicsdb_round1_resource_selection.md`: perform
  metadata-only resource selection for Round 1.5 logical bundles.
- `prompts/curation/stomicsdb_round15_acquisition_plan.md`: materialize the
  two-column Round 1.5 acquisition plan from effective-intake-approved bundles.
- `prompts/curation/stomicsdb_round2b_bundle_validation.md`: validate one
  approved bundle structurally after Round 2A without scientific analysis or
  case admission.

Round 3 uses the five-prompt family under
`prompts/curation/stomicsdb/round3/`: `implementation_window.md`,
`dataset_worker.md`, `article_reader.md`, `resource_access_researcher.md`, and
`case_reviewer.md`. The standalone review authority is
`checklists/stomicsdb/round3/case_review.md`; the sole accepted-field authority
is `output_template/stomicsdb/round3/case_outputs.md`. The dataset worker is the
only formal writer. Leaf roles return fixed evidence, and the reviewer returns
findings for at most two rounds.

STOmicsDB dual-chain construction uses the lightweight candidate controller at
`prompts/curation/stomicsdb/dual_chain/candidate_job.md`, the output contract at
`output_template/stomicsdb/dual_chain/outputs.md`, and the operational workflow
at `docs/datasets/stomicsdb-dual-chain-workflow.md`. It reuses the shared
scientific/execution JSONL schemas and adds only strict job-assignment and chain
manifest schemas plus a small terminal job-response schema.

STOmicsDB dispatch prompts:

- `prompts/curation/dispatch_stomicsdb_round1_article_worker.md`
- `prompts/curation/dispatch_stomicsdb_round1_batch.md`
- `prompts/curation/dispatch_stomicsdb_round1_resource_selection_worker.md`
- `prompts/curation/dispatch_stomicsdb_round1_resource_selection_batch.md`
- `prompts/curation/dispatch_stomicsdb_round2b_bundle_worker.md`
- `prompts/curation/dispatch_stomicsdb_round2b_batch.md`

The STOmicsDB contracts are synchronized through effective-intake-aware Round
1.5 planning, Round 2B structural localization, and the active Round 3
dataset-scoped case contract. Each Round 3 candidate is one public-data
dual-chain dispatch scope. The dual-chain prompts select `case_route:
tool_method | public_database_stomicsdb`; the public route consumes the
canonical three-file case directly and does not require the tool/method
screening layout. Task admission, hidden references, and benchmark evaluation
remain downstream.
`scripts/stomicsdb_round2_download.py` implements the operator-started Round 2A
transfer capability. `scripts/start_stomicsdb_round2_download.sh` validates the
plan and starts that downloader under `nohup` only when an operator invokes the
launcher; publishing a plan or script never starts it automatically.

All tool/method curation prompts write under
`raw_data/tool_method/<method_slug>/` and should not create the legacy split
layout.

- `prompts/curation/tool_method_case_screening.md`: screen source material for
  eligible tool/method cases before localization.
- `prompts/curation/tool_method_case_localization.md`: localize source material
  and case data for each screened case before dual-chain extraction, with
  route completion, Case-reference reuse, YAML-parseable manifests, controlled
  final status/visibility values, and source-supported rebuild when needed.
- `prompts/curation/dual_chain_extraction.md`: construct draft case-derived
  dual-chain artifacts from localized source and data records.
- `prompts/curation/dual_chain_independent_check.md`: write a per-chain `independent_check.md`
  checklist review, update the manifest summary, and confirm procedural chain quality
  for drafted chains.

Dispatch prompts are subagent entries and must be used with their mandatory
stage protocol:

- `prompts/curation/dispatch_tool_method_case_localization.md`
- `prompts/curation/dispatch_dual_chain_extraction.md`
- `prompts/curation/dispatch_dual_chain_independent_check.md`

Registry-scale orchestration wrappers reuse the stage prompts above and do not
define new curation workflows:

- `prompts/curation/dispatch_tool_method_stage1_2_method_worker.md`
- `prompts/curation/dispatch_tool_method_stage3_method_worker.md`
- `prompts/curation/dispatch_dual_chain_stage4_batch_worker.md`

`config_templates/` contains reusable configuration templates. Experiment
packages own run-specific copies.

`task_registry_template/` contains the lightweight Git-side registry entry
template. Complete task bundles live under the NAS data root.

`submission_contract.yaml` records the shared submission files, workspace
subdirectories, and schema paths. Experiment evaluator configs should reference
this contract rather than redefining it.

`schemas/` contains JSON Schema placeholders and future schema contracts for
submissions, task manifests, data manifests, and reference anchors.

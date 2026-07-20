# Contracts

This directory stores HypoTrace contract assets: agent-facing output controls,
condition-specific input templates, prompt templates, config templates, task
registry templates, schema placeholders, and shared submission requirements.

## Layout

```text
contracts/
  HYPO_TRACE_SKILL.md
  output_template/
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

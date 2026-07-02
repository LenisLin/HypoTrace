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
  schemas/
```

`HYPO_TRACE_SKILL.md` and `output_template/` are the shared output contract for
all model-harness-conditions. Runner preparation may copy them into a sandbox as
`HYPO_TRACE_SKILL.md` and `output_template/`, but the repository source of truth
lives here.

`skills/` contains condition-specific templates for B/C inputs. These templates
must not replace or modify the shared output contract.

`prompts/` contains reusable prompt templates. Agent-facing prompts must not
include hidden references, scoring rubrics, or evaluator prompts.

`config_templates/` contains reusable configuration templates. Experiment
packages own run-specific copies.

`task_registry_template/` contains the lightweight Git-side registry entry
template. Complete task bundles live under the NAS data root.

`submission_contract.yaml` records the shared submission files, workspace
subdirectories, and schema paths. Experiment evaluator configs should reference
this contract rather than redefining it.

`schemas/` contains JSON Schema placeholders and future schema contracts for
submissions, task manifests, data manifests, and reference anchors.

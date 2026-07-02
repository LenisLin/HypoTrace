# Adapter Contract

Runner adapters connect HypoTrace to model-harness systems. They prepare a
sandbox, launch a harness, collect passive logs, and collect the final
submission. They must not correct the agent during the run.

## Base Interface

```python
class BaseAgentAdapter:
    name: str

    def prepare(self, run_dir, task_package, condition_config):
        """Create workspace, copy prompt/template/data, and inject condition files."""

    def run(self, run_dir, model_config, budget_config):
        """Launch the agent harness without active HypoTrace repair feedback."""

    def collect(self, run_dir):
        """Collect submission and passive logs after the harness exits."""

    def summarize(self, run_dir):
        """Return a run record for downstream evaluation."""
```

## Shared Runner Duties

- Create a sandbox run directory.
- Copy `task_prompt.md`, the shared output skill from
  `contracts/HYPO_TRACE_SKILL.md`, the shared template from
  `contracts/output_template/`, and allowed data mounts.
- Inject condition-specific files.
- Launch the selected harness with fixed budgets.
- Record run metadata.
- Collect submission files.
- Collect logs passively.

## Prohibited Runner Behavior

- Real-time validator-assisted correction.
- Auto-filling missing HypoTrace fields.
- Copying hidden references into the agent workspace.
- Providing scoring rubrics or evaluator prompts to the agent.
- Giving C condition an automatic trace logger advantage.

## Condition Inputs

Condition A:

```text
HYPO_TRACE_SKILL.md
task_prompt.md
data/
output_template/
generic Python/R/shell environment
```

Condition B:

```text
Condition A inputs
EASY_BIO_SKILL.md
method names, links, common pitfalls, and best-practice checklist
```

Condition C:

```text
Condition A inputs
BIOHARNESS_README.md
bioharness access configuration
generic Python/R/shell environment
```

All conditions must submit the same HypoTrace format.
Condition-specific templates are sourced from `contracts/skills/`.

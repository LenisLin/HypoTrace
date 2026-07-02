# Task Registry Template

This directory is the Git-side template for a lightweight task registry entry.
It is not a complete task bundle.

Expected Git registry entry:

```text
tasks/<task_id>/
  task_manifest.yaml
  task_prompt.md
  data_manifest.yaml
  README.md
```

The complete task bundle lives under:

```text
/mnt/NAS_21T/ProjectData/HypoTrace_Data/tasks/<task_id>/
```

Files such as `environment.yml`, `run_reference.sh`, `starter_workspace/`,
agent-visible data mounts, hidden references, truth files, curation notes, and
reference outputs belong in the NAS task bundle, an experiment sandbox, or
evaluator-only storage according to visibility. They are not part of the Git
registry template by default.

# Tasks

`tasks/` is the Git task registry/index. It is not the storage area for complete
task bundles.

Each real task registry entry should use this lightweight shape:

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

Hidden references, truth files, reference outputs, raw data, prepared data,
trajectories, submissions, and run outputs must not be stored in this Git
repository.

`examples/toy_task` is a smoke fixture for current loader and CLI checks. It is
not the target storage pattern for real benchmark tasks.

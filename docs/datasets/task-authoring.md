# Task Authoring

Each real HypoTrace task has a lightweight Git registry entry and a complete NAS
task bundle. Reference files define non-exclusive scientific anchors. Scoring
logic belongs to evaluator code, hidden evaluator material, or
experiment-specific evaluator configuration.

## Required Files

Git registry required files:

```text
tasks/<task_id>/
  task_manifest.yaml
  task_prompt.md
  data_manifest.yaml
  README.md
```

- `task_prompt.md`: agent-facing task instruction.
- `task_manifest.yaml`: task identity, benchmark controls, prompt path, and NAS
  bundle locator.
- `data_manifest.yaml`: NAS locator, checksum metadata, and data access class.
- `README.md`: human-readable registry notes and visibility constraints.

NAS full bundle expected layout:

```text
/mnt/NAS_21T/ProjectData/HypoTrace_Data/tasks/<task_id>/
  input/
  data/
  starter_workspace/
  references/
  manifests/
  curation/
```

The NAS full bundle stores agent-visible inputs, large data, reproducibility
support, evaluator-only references, and curation material according to
visibility. Reference chains and truth files must not be stored in Git task
registry entries.

Optional files:

- `starter_workspace/`: non-answer starting files exposed to the agent, stored
  in the NAS bundle or copied into an experiment sandbox.
- `environment.yml`, `Dockerfile`, or shell scripts for reproducibility support,
  stored in the NAS bundle or experiment sandbox as appropriate.

## Authoring Workflow

1. Choose one of the four task source routes: public dataset, benchmark
   research, bioinformatics tool paper, or biomedical analysis paper.
2. Define the agent-facing biological question in `task_prompt.md`.
3. Record NAS locators, access class, and checksums in `data_manifest.yaml`.
4. Record task identity, controls, and NAS bundle location in
   `task_manifest.yaml`.
5. Place reference scientific chains, reference execution chains, reference
   claim surfaces, and curation notes in the NAS bundle or evaluator-only
   storage.
6. Keep truth files, grading rubrics, evaluator prompts, and reference anchors
   out of the agent-visible workspace.

## Validity Requirement

Task prompts must not leak hidden reference chains, truth files, or grading
rubrics. Publication-derived chains are candidate anchors. They are not automatic
ground truth and should not force agents to reproduce a paper's exact path.

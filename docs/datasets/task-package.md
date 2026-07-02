# Task Package

HypoTrace converts public dataset, benchmark research, bioinformatics tool paper,
and biomedical analysis paper sources into a two-layer task structure.

Git registry entry:

```text
tasks/<task_id>/
  task_manifest.yaml
  task_prompt.md
  data_manifest.yaml
  README.md
```

NAS full task bundle:

```text
/mnt/NAS_21T/ProjectData/HypoTrace_Data/tasks/<task_id>/
  input/
  data/
  starter_workspace/
  references/
  manifests/
  curation/
```

Scoring logic is not part of the Git registry entry. It belongs to evaluator
code, hidden evaluator material, or experiment-specific evaluator configuration.
The Git registry entry is reviewable and diffable. It contains agent-facing
prompt text and locators/checksums, not full benchmark data.

The NAS full task bundle stores large data, agent-visible input material, and
evaluator-only references. Hidden references, truth files, reference outputs,
and curation-only material must not be copied into the agent workspace.
Publication-derived chains are evaluator-only anchors; they are not unique truth
trajectories and should not force agents to reproduce a paper's exact path.

The current `examples/toy_task` layout remains a smoke fixture for loader and
CLI compatibility. Registry loading and NAS bundle resolution are later
implementation steps.

## `task_manifest.yaml`

Records task identity and benchmark controls:

- `task_id`
- `task_name`
- `task_level`
- `source_route`
- `modality`
- `domain`
- `allowed_conditions`
- `expected_submission`
- `nas_bundle_root`
- `budget`

`expected_submission` should name the HypoTrace submission protocol without a
version label.

## Source Routes

### Public Dataset Route

Placeholder for public dataset source selection, retrieval, organization,
reference-chain construction, review, and task packaging.

### Benchmark Research Route

Placeholder for benchmark research source selection, task reconstruction,
reference-chain construction, review, and task packaging.

### Bioinformatics Tool Paper Route

Placeholder for bioinformatics tool paper source selection, reproducibility
review, reference-chain construction, and task packaging.

### Biomedical Analysis Paper Route

Placeholder for biomedical analysis paper source selection, claim and evidence
review, reference-chain construction, and task packaging.

## `data_manifest.yaml`

Records NAS locators, checksum metadata, and data access class. It should not
store raw data, hidden references, truth files, reference outputs, or complete
trajectories.

## Reference Anchors

Reference anchors belong in the NAS full task bundle or evaluator-only storage,
for example:

```text
/mnt/NAS_21T/ProjectData/HypoTrace_Data/tasks/<task_id>/references/
```

They may include reference scientific chains, reference execution chains,
reference claim surfaces, and curation notes. Runner preparation must not copy
them into the agent workspace. Agents receive `task_prompt.md`, the shared
output contract from `contracts/HYPO_TRACE_SKILL.md` and
`contracts/output_template/`, agent-visible data/input material, and optional
condition-specific files only.

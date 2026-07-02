# Data Contract

The default data root is `/mnt/NAS_21T/ProjectData/HypoTrace_Data`.

Required subdirectories:

- `raw/`: immutable downloaded or externally supplied input data.
- `prepared/`: normalized data prepared for benchmark runs.
- `tasks/`: complete NAS task bundles keyed by task id.
- `references/`: hidden truth files, reference outputs, and evaluator-only anchors.
- `runs/`: per-run submissions, manifests, logs, artifacts, scores, and summaries.
- `trajectories/`: agent messages, tool calls, notebooks, or equivalent traces.
- `results/`: aggregated benchmark outputs.
- `logs/`: cross-run operational logs.
- `cache/`: reusable downloads and intermediate caches.
- `manifests/`: dataset and task manifest snapshots.

## Run Layout

Each run should write to:

```text
runs/<task_id>/<run_id>/
  input/
    task_prompt.md
    HYPO_TRACE_SKILL.md
    output_template/
    data/
  agent_workspace/
  submission/
    trace_manifest.json
    scientific_chain.jsonl
    execution_subchains.jsonl
    artifacts.jsonl
    final_claims.json
    final_report.md
    workspace/
      scripts/
      notebooks/
      figures/
      tables/
      logs/
  logs/
    harness_stdout.log
    harness_stderr.log
    tool_calls.jsonl
    token_usage.json
    run_meta.json
  eval/
    validation_report.json
    trace_graph.json
    score_report.json
    metric_table.csv
    evaluator_notes.md
```

The `submission/` directory is the common output protocol shared by all
model-harness-conditions and is the agent submission. The `eval/` directory
stores post-hoc evaluator outputs; `score_report.json` and `metric_table.csv`
are not agent submissions.

`runs/<task_id>/<run_id>/` is the canonical layout for benchmark runners. The
current dry-run skeleton may still write to `runs/<run_id>/` with root-level
`artifacts/`, `scores.json`, and `summary.csv`; that simplified layout is only
a contract smoke test and should not define the final runner layout.
Tests for this layout should be treated as smoke-test compatibility checks, not
as acceptance tests for the final benchmark run directory.

The `input/` directory contains only agent-visible material. It may contain the
task prompt, shared HypoTrace output skill, shared output template, and mounted
data. The shared output controls are sourced from `contracts/HYPO_TRACE_SKILL.md`
and `contracts/output_template/`. It must not contain hidden references, scoring
rubrics, evaluator prompts, or curation-only reference chains.

## Hidden References

Task-specific hidden references may live under
`tasks/<task_id>/references/`, `references/<task_id>/`, or an equivalent
evaluator-only path. They may include truth files, hidden chokepoints, expert
curation notes, and grading assets. Agent input may only be copied from
agent-visible material in the task bundle, such as `input/`, visible data
mounts, or approved starter workspace files. Do not expose hidden references in
agent-facing prompts or starter workspaces.

Do not store raw datasets, reference answers, submissions, trajectories, or
grading outputs in the Git repository.

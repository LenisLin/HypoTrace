# Run Directory

Each benchmark run should be isolated in a sandbox directory under the NAS data
root or another configured output root.

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

## Input

`input/` contains agent-visible files only. It may include the task prompt, the
shared output skill, the shared output template, mounted data, and allowed
condition-specific files.

The shared output skill and output template are sourced from
`contracts/HYPO_TRACE_SKILL.md` and `contracts/output_template/`, then copied
into the sandbox as `HYPO_TRACE_SKILL.md` and `output_template/`.

`input/` must not contain hidden references, curation-only chains, scoring
rubrics, evaluator prompts, or answer keys.

## Agent Workspace

`agent_workspace/` is the harness working area. It may contain transient files,
tool state, package caches, or notebooks created during the run. Durable
evidence artifacts should be copied or written into `submission/workspace/`.

## Submission

`submission/` is the agent output. It is the only directory evaluated as the
agent-facing HypoTrace submission contract.

## Logs

`logs/` stores passive harness logs, tool call records, token usage when
available, and run metadata. Missing token usage should be recorded as missing.

## Eval

`eval/` stores evaluator outputs. These files are produced after the run and are
not part of the agent submission.

## Anonymous Ranking Packets

Ranking packets should be exported separately from identity-bearing run
metadata, for example:

```text
annotation_packets/<task_id>/<pair_id>/
  run_A_scientific_chain.md
  run_B_scientific_chain.md
  run_A_execution_summary.md
  run_B_execution_summary.md
  run_A_final_report.md
  run_B_final_report.md
  rubric.md
```

The packet generator should support blind pairwise ranking through the same HVU
renderer for human and agent candidates. It should keep source identity hidden
until judgments are fixed and report ranking alongside, but not in place of,
objective integrity diagnostics.

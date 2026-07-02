# Starter Workspace Preview

This directory describes what a benchmark agent would see for the GBM Hypoxia-TAM demo task.

## Visible Materials

The agent workspace should contain:

```text
task_prompt.md
data_manifest.yaml
starter_workspace/
  README.md
  input/
    scrna/
    visium/
    histology/
    annotations/
  scripts/
  notebooks/
contracts/
  HYPO_TRACE_SKILL.md
  output_template/
```

## Expected Submission Files

The agent must produce:

```text
trace_manifest.json
scientific_chain.jsonl
execution_subchains.jsonl
artifacts.jsonl
final_claims.json
final_report.md
```

## Hidden From Agent In A Real Benchmark

This public demo folder includes the following gold/reference files for review.
In a real hidden benchmark, the agent workspace must not contain:

```text
reference_scientific_chain.json
reference_claim_surface.json
reference_execution_chain.json
curation_notes.md
quality_rubric.md
analysis_logic_chain_*.jsonl
```

## Task Boundary

The task is to generate an evidence-grounded analysis trace from the provided data. In a real benchmark, the agent should not reproduce a hidden reference exactly and should not infer hidden evaluator answers from task packaging. In this public demo, the reference files are visible only to show the intended curation output shape.

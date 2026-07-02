# HypoTrace Output Skill

Use this file as the common agent-facing output skill for all HypoTrace
model-harness-conditions.

## Purpose

HypoTrace records whether a bioinformatics agent can turn an analysis question
into an auditable hypothesis-to-evidence trace. The submission must show how
biological conclusions are connected to data, method intent, code, parameters,
results, and artifacts.

This skill defines the output protocol only. It does not contain task answers,
reference chains, scoring rubrics, hidden evaluator criteria, or task-specific
hints.

## Required Submission Layout

Submit the following directory structure:

```text
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
```

## Scientific Chain

Each line of `scientific_chain.jsonl` is one hypothesis-verification unit.
Record:

- `scientific_unit_id`
- `unit_type`
- `parent_units`
- `question_or_hypothesis`
- `evidence_need`
- `method_intent`
- `execution_subchain_ids`
- `result`
- `conclusion`
- `next_question`

Separate computational observations from biological interpretation:

```text
Result = what the data and computation showed
Conclusion = the biological inference drawn from that result
```

Avoid causal or clinical validity claims unless the task data and design support
them. Association, co-expression, enrichment, or spatial proximity should be
reported with the appropriate scope.

## Execution Subchains

Each line of `execution_subchains.jsonl` describes one execution subchain linked
to a scientific unit. Include the stage question, execution goal, executed steps,
parameters, code paths, output artifacts, status, and result extraction.

Code and notebook paths should point inside `workspace/scripts/` or
`workspace/notebooks/` when available.

## Artifacts

Each line of `artifacts.jsonl` describes one file created or used by the
analysis. Include artifact type, path, creator step, inputs, checksum when
available, a short summary, and validation status. Paths should point to files
inside `workspace/figures/`, `workspace/tables/`, `workspace/logs/`, or another
submission workspace subdirectory.

## Final Claims

`final_claims.json` should list final biological claims and link each claim to
supporting scientific units, execution subchains, and artifacts.

Represent support as an evidence vector rather than only as a single label.
Useful evidence dimensions include marker support, group association, sample
consistency, spatial coherence, statistical rigor, artifact traceability, and
overclaim penalty.

## Validation Policy

HypoTrace uses post-hoc validation after the run. During the main experiment,
agents should not receive real-time validator feedback that asks them to repair
missing fields. Format failures are evaluated after submission as schema failure
or partial compliance.

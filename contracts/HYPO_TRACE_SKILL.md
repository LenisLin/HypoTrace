# HypoTrace Output Skill

Use this file as the common agent-facing output skill for all HypoTrace
model-harness-conditions.

## Purpose

HypoTrace records whether a bioinformatics agent can turn an analysis question
into an auditable hypothesis-to-evidence trace. The submission must show how
scientific conclusions are connected to study framing, execution subchains,
code, parameters, results, and artifacts.

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

`scientific_chain.jsonl` contains one isolated `S00` study-framing record
followed by one or more hypothesis-verification unit (HVU) records. Record:

- `scientific_unit_id`
- `parent_units`
- `S00` `data_summary`
- `hypothesis`
- `experiment.summary`
- `experiment.execution_subchain_ids`
- `result.observations[]`
- observation `observation`, `support`, and `interpretation`
- `conclusion.summary`
- `next_hypothesis`

Link scientific units to execution only through
`experiment.execution_subchain_ids`. Record input objects, calls, parameters,
outputs, and source locators in `execution_subchains.jsonl`.

Create a new HVU when the analysis enters a new hypothesis -> experiment ->
result -> conclusion progression. Do not split one HVU only because the same
hypothesis uses multiple markers, features, plots, display formats, code cells,
or intermediate output objects.

Separate computational observations from biological interpretation:

```text
Result = what the data and computation showed
Conclusion = the scientific interpretation drawn from that result
```

For substantive HVUs, `result.observations[]` should record concrete
computational observations when produced, including task-specific names, values,
output objects, or statistical summaries. Each observation records what was
observed, the support used, and the bounded interpretation. Do not replace
result material with only conclusion-like prose.

Represent scope, uncertainty, and unsupported limits in bounded prose inside
`conclusion.summary` and in `final_claims` evidence vectors when they affect
final claims.

Avoid causal or clinical validity claims unless the task data and design support
them. Association, co-expression, enrichment, or spatial proximity should be
reported with the appropriate scope.

## Execution Subchains

Each line of `execution_subchains.jsonl` describes one execution subchain linked
to a scientific unit. The subchain records the method-call surface that turns
the linked experiment into result material.

By default, each HVU should have one primary execution subchain that reaches the
result material for that HVU. Do not use one generic tool-running subchain to
support multiple distinct HVUs.

Use the minimal outer record: `execution_subchain_id`,
`linked_scientific_unit_id`, `steps`, and `result_extraction`.

Use ordered multi-step routes when multiple calls are needed to reach the linked
HVU's result material. Each step must follow input -> call(parameters) -> output
order. Record object inputs, call, key parameters, outputs, and `source_ref`.
`source_ref` may point to submitted workspace material such as a script,
notebook cell, log, or artifact; to an agent-visible task material location; or
be null when unavailable. When present, `source_ref` uses
`{"type":"...","locator":"..."}`.

When a step consumes a prior output, reuse the prior output object ID as the
input ID. The same object ID should refer to the same logical object throughout
the submission.

Use `result_extraction.observations[]` to record observations extracted from the
route. These observations should align with the linked HVU
`result.observations[]` and use the same `observation`, `support`, and
`interpretation` shape.

## Artifacts

Each line of `artifacts.jsonl` describes one file created or used by the
analysis. Include artifact type, path, creator step, inputs, checksum when
available, a short summary, and validation status. Paths should point to files
inside `workspace/figures/`, `workspace/tables/`, `workspace/logs/`, or another
submission workspace subdirectory.

## Final Claims

`final_claims.json` should list final scientific claims and link each claim to
supporting scientific units, execution subchains, and artifacts.

When a claim depends on a child HVU, include the child HVU and any parent HVUs
needed for the claim, together with their execution subchains and artifacts.

Represent support as an evidence vector rather than only as a single label.
Useful evidence dimensions include marker support, group association, sample
consistency, spatial coherence, statistical rigor, artifact traceability, and
overclaim penalty.

## Validation Policy

HypoTrace uses post-hoc validation after the run. During the main experiment,
agents should not receive real-time validator feedback that asks them to repair
missing fields. Format failures are evaluated after submission as schema failure
or partial compliance.

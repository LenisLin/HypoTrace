# Architecture

HypoTrace separates benchmark protocol, task data, agent execution, evaluator
logic, and reports. Code, contract assets, documentation, experiment specs, and
lightweight task registry entries live in Git. Complete task bundles and hidden
evaluator material live under the NAS data root.

## Modules

1. `spec`: defines submission schemas, task registry schemas, shared templates,
   and the common output skill.
2. `tasks`: resolves Git task registry entries and, in later implementation, NAS
   task bundle locators. The current loader remains a smoke-fixture loader until
   registry loading is designed.
3. `runner`: prepares sandbox runs, injects condition-specific inputs, launches
   model-harness-conditions, and collects submissions without active correction.
4. `evaluation`: performs post-hoc parse validation, trace graph construction,
   deterministic metrics, reference alignment, claim checks, and aggregation.
5. `reporting`: produces audit reports, summary tables, leaderboards, and
   annotation packets for companion ranking.

`datasets` remains a helper boundary for NAS data root resolution and manifest
handling. It is not a separate benchmark layer.

The canonical shared output controls live at `contracts/HYPO_TRACE_SKILL.md`
and `contracts/output_template/`. Runner preparation may copy them into the
sandbox as `HYPO_TRACE_SKILL.md` and `output_template/`. The
`contracts/skills/` directory stores condition-specific templates and must not
create a different output protocol for any condition.

## Data Flow

```text
Task registry entry and NAS bundle
  -> Runner prepares sandbox
  -> Agent receives task prompt, common skill, output template, and data
  -> Agent writes submission
  -> Post-hoc validator parses the submission
  -> Trace graph builder links scientific units, execution, artifacts, and claims
  -> Metric calculators produce objective reports
  -> Reporting exports summaries and annotation packets
```

## Package Boundaries

- `hypotrace.spec`: schema models, validators, and JSON Schema export.
- `hypotrace.datasets`: data root and manifest handling.
- `hypotrace.tasks`: smoke-fixture task loading today; later Git registry and
  NAS bundle resolution. Do not use the current loader as evidence that registry
  entries are validated.
- `hypotrace.runners`: benchmark execution and dry-run submission contracts.
- `hypotrace.graders`: legacy evaluator adapters and score contracts.
- `hypotrace.evaluation`: parse validation, trace graphs, objective metrics,
  reference alignment, claim checks, and aggregation.
- `hypotrace.reporting`: export of summaries, tables, figures, and ranking inputs.

## Design Boundary

Evaluator configuration is not benchmark data. Scoring logic and judge prompts
belong in evaluator code, hidden evaluator material, or experiment-specific
evaluator configs. Contract-level submission requirements belong in
`contracts/`.

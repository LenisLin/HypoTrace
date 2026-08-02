# Architecture

HypoTrace is an evaluation harness that separates versioned benchmark workloads,
task data, agent execution, trace normalization, evaluator logic, and reports.
Code, contract assets, documentation, experiment specs, and lightweight task
registry entries live in Git. Complete task bundles, human and baseline-agent
anchor results, and hidden evaluator material live under the NAS data root.

## Modules

1. `spec`: defines submission schemas, task registry schemas, shared templates,
   and the common output skill.
2. `tasks`: will resolve Git task registry entries and NAS task bundle locators;
   the registry loader has not yet been designed or implemented.
3. `runner`: prepares sandbox runs, injects condition-specific inputs, launches
   model-harness-conditions, and collects submissions without active correction.
4. `evaluation`: performs post-hoc parse validation, trace graph construction,
   deterministic integrity metrics, non-exclusive reference diagnostics, claim
   checks, anonymized ranking, and aggregation.
5. `reporting`: produces audit reports, summary tables, human-relative
   leaderboards, and blinded annotation packets.

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
  -> Integrity and scientific-scope checks produce diagnostic reports
  -> Common renderer anonymizes human and agent HVU chains
  -> Pairwise or listwise judges rank scientific quality without source identity
  -> Aggregation reports human-relative and baseline-agent-relative performance
```

## Package Boundaries

- `hypotrace.spec`: schema models, validators, and JSON Schema export.
- `hypotrace.datasets`: data root and manifest handling.
- `hypotrace.tasks`: reserved for future Git registry and NAS bundle resolution;
  no current loader validates registry entries.
- `hypotrace.runners`: reserved for future benchmark execution contracts and
  model-harness adapters.
- `hypotrace.graders`: legacy evaluator adapters and score contracts.
- `hypotrace.evaluation`: parse validation, trace graphs, integrity metrics,
  non-exclusive reference diagnostics, claim checks, anonymous ranking, and
  aggregation.
- `hypotrace.reporting`: export of summaries, tables, figures, and ranking inputs.

## Design Boundary

Evaluator configuration is not benchmark data. Scoring logic and judge prompts
belong in evaluator code, hidden evaluator material, or experiment-specific
evaluator configs. Contract-level submission requirements belong in
`contracts/`.

Benchmark cases instantiate the harness; they do not define it. A comparable
score must identify the benchmark version, task set, resource policy, anchor
pool, anonymization renderer, judge configuration, and aggregation method.

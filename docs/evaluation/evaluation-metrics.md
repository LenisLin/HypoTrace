# Evaluation Metrics

HypoTrace metrics are organized around scientific hypotheses rather than a single
large total score. The first implementation should distinguish comparative
scientific-quality endpoints from protocol and evidence-integrity diagnostics.

Primary comparative endpoints for open-ended tasks should be limited to:

- Human-Relative Preference Probability.
- Baseline-Agent-Relative Preference Probability.
- Judge Agreement.
- Task-Level Ranking Uncertainty.

The first integrity dashboard should report:

- Trace Parseability.
- HVU Completeness.
- Result-Conclusion Separation Rate.
- Artifact Validity Rate.
- Scientific-Execution Linkage.
- Evidence-Backed Claim Rate.
- Overclaim Rate.

Integrity metrics constrain interpretation of a ranked result; they are not a
substitute for scientific-quality comparison. Other metrics are exploratory
until their extraction logic, missing-data behavior, and failure modes are
specified and tested.

## Descriptive Metrics

- Wall-clock time.
- Total turns.
- Total input tokens.
- Total output tokens.
- Tool calls.
- Execution steps.
- HVU count.
- Artifact count.
- Cost.
- Context tokens.

These describe behavior and cost. They are not automatically good or bad.

## Protocol Validity

- Trace Parseability: valid required fields divided by all required fields.
- HVU Completeness: complete HVUs divided by total HVUs.
- Result-Conclusion Separation Rate: HVUs with distinct result and conclusion
  divided by total HVUs.

## Execution Quality

Runtime status and code provenance metrics apply to agent-run extensions and
logs, not to the shared case-derived execution core.

- Artifact Validity Rate: existing and readable artifacts divided by declared artifacts.
- Agent-Run Execution Completion Rate: runtime-successful extension/log steps
  divided by declared runtime steps.
- Agent-Run Code Provenance Coverage: extension/log steps with code provenance
  divided by declared runtime steps.
- Core Parameter Recording Rate: shared-core execution steps with non-empty
  `parameters` divided by declared core execution steps.

## Scientific-Execution Coupling

- Scientific-Execution Linkage: non-framing HVUs with execution subchains divided
  by non-framing HVUs.
- Evidence-Backed Claim Rate: final claims with data-to-execution-to-artifact-to-result
  paths divided by final claims.
- Orphan Execution Rate: execution subchains without linked HVUs divided by all
  execution subchains.
- Unsupported Conclusion Rate: conclusions without supporting result or artifact
  divided by all conclusions.

## Reference Alignment

Reference alignment is a non-exclusive diagnostic. It should not require
reproducing a publication path or penalize a valid alternative analysis. A
case-derived human chain records an observed human choice, not the answer key.

- Critical Chokepoint Recall.
- Chokepoint Precision.
- Chokepoint F1.

## Final Claim Quality

Final claim compatibility may be categorized as compatible, valid alternative,
unsupported, contradicted, or overclaimed. The primary representation should be
an evidence vector, not a single subjective label.

Example evidence vector dimensions:

- marker support.
- group association.
- sample consistency.
- spatial coherence.
- statistical rigor.
- artifact traceability.
- overclaim penalty.

## Context Metrics

- Context Load Ratio: historical context tokens divided by total input tokens.
- Trace Compression Ratio: final trace tokens divided by raw transcript tokens.
- Context Efficiency: primary quality score divided by total input tokens.

## Anonymous Human-Relative Ranking

For each task, mix human and agent results in one anonymized candidate pool.
Ranking prompts should judge scientific question alignment, method-data fit,
evidence traceability, robustness, and conclusion scope without asking judges to
identify the source. Reveal candidate identities only after ranking.

- Human-Relative Preference Probability: estimated probability that an agent
  result is preferred to the human anchor for the same task.
- Baseline-Agent-Relative Preference Probability: estimated probability that a
  new result is preferred to a frozen baseline-agent result.
- Judge Agreement: agreement across blinded judges before aggregation.
- Task-Level Ranking Uncertainty: uncertainty estimated with the task as the
  aggregation unit.

Pairwise judgments may be aggregated with Bradley-Terry or Plackett-Luce models.
A reported score must identify the benchmark version, task set, anchor pool,
anonymization renderer, judge configuration, and aggregation method. The score
is relative to that evaluation context and does not estimate absolute scientific
correctness.

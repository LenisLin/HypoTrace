# Evaluation Metrics

HypoTrace metrics are organized around scientific hypotheses rather than a single
large total score. The first implementation should provide a dashboard and a
small number of primary endpoints.

Primary endpoints for the first real benchmark should be limited to:

- Trace Parseability.
- HVU Completeness.
- Result-Conclusion Separation Rate.
- Artifact Validity Rate.
- Scientific-Execution Linkage.
- Evidence-Backed Claim Rate.
- Overclaim Rate.

Other metrics are exploratory until their extraction logic, missing-data
behavior, and failure modes are specified and tested.

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

- Execution Completion Rate: successful execution steps divided by declared steps.
- Artifact Validity Rate: existing and readable artifacts divided by declared artifacts.
- Code Provenance Coverage: execution steps with code path divided by declared steps.
- Parameter Recording Rate: execution steps with parameters divided by declared steps.

## Scientific-Execution Coupling

- Scientific-Execution Linkage: non-planning HVUs with execution subchains divided
  by non-planning HVUs.
- Evidence-Backed Claim Rate: final claims with data-to-execution-to-artifact-to-result
  paths divided by final claims.
- Orphan Execution Rate: execution subchains without linked HVUs divided by all
  execution subchains.
- Unsupported Conclusion Rate: conclusions without supporting result or artifact
  divided by all conclusions.

## Reference Alignment

Reference alignment should not require reproducing the publication path. It
should evaluate coverage of critical analysis logic.

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

## Companion Ranking

For open research questions, retain blind pairwise expert ranking as companion
evaluation. Ranking prompts should separately judge scientific chain quality,
execution chain quality, and final report quality. Aggregation can use
Bradley-Terry or Elo-style models with expert agreement analysis.

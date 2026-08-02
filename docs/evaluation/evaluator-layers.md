# Evaluator Layers

HypoTrace evaluation is post-hoc. Evaluator code reads the completed submission,
hidden references, and passive logs after a run has ended.

Runtime status and code provenance metrics apply to agent-run extensions and
logs, not to the shared case-derived execution core.

## Layer 0: File And Parse Validation

Checks:

- `submission/` exists.
- `trace_manifest.json` exists and parses.
- `scientific_chain.jsonl` parses line by line.
- `execution_subchains.jsonl` parses line by line.
- `artifacts.jsonl` parses line by line.
- `final_claims.json` parses.
- `final_report.md` exists.

Output:

```json
{
  "parse_status": "valid",
  "missing_files": [],
  "json_errors": []
}
```

## Layer 1: Schema Metrics

Metrics:

- Trace Parseability.
- HVU Completeness.
- Result-Conclusion Separation Rate.
- Required Field Coverage.

## Layer 2: Artifact Metrics

Checks:

- Artifact paths exist.
- Files are readable.
- Checksums match when declared.
- Artifact types are plausible.
- `created_by` points to a valid execution step.

Metrics:

- Artifact Validity Rate.
- Artifact Provenance Coverage.

## Layer 3: Trace Graph Construction

Graph nodes:

- ScientificUnitNode.
- ExecutionSubchainNode.
- ExecutionStepNode.
- DataObjectNode.
- ArtifactNode.
- ClaimNode.

Edges:

- ScientificUnit requires ExecutionSubchain.
- ExecutionSubchain contains ExecutionStep.
- ExecutionStep consumes DataObject.
- ExecutionStep produces DataObject.
- Artifact materializes DataObject.
- ExecutionStep produces Artifact.
- ScientificUnit depends on parent ScientificUnit.
- ScientificUnit observes Result.
- Claim derives from direct and required parent ScientificUnit nodes.
- Claim is supported by Artifact.

Metrics:

- Scientific-Execution Linkage.
- Evidence-Backed Claim Rate.
- Orphan Execution Rate.
- Unsupported Conclusion Rate.
- Core Parameter Recording Rate.
- Core Source Reference Coverage.

Runtime-only metrics such as execution completion and code provenance coverage
are computed from agent-run extensions or logs. They must not require `status`
or `code_path` fields inside shared-core `execution_subchains.jsonl`.

## Layer 4: Non-Exclusive Reference Diagnostics

Case-derived human chains record observed analysis choices rather than required
paths. Reference diagnostics may compare agent HVUs, execution subchains, and
claims against non-exclusive analysis anchors, acceptable method families, and
claim surfaces. They must not treat failure to reproduce a publication route as
scientific failure when the agent provides a valid alternative analysis.

Supported matcher classes may include rule-based matching, controlled vocabulary
matching, embedding similarity, fixed-rubric LLM judging, and expert audit
subsets. LLM judging must be auditable and must not become the only primary
score.

Metrics:

- Critical Chokepoint Recall.
- Chokepoint Precision.
- Chokepoint F1.

These metrics are diagnostic. They are not the primary scientific-quality score
for open-ended tasks.

## Layer 5: Claim Quality

Final claims should be represented through evidence vectors rather than only
through unsupported categorical labels.

Metrics:

- Evidence-Backed Claim Rate.
- Final Claim Compatibility.
- Overclaim Rate.
- Claim Scope Correctness.

Typical overclaims:

- Association to causation.
- Single dataset to clinical biomarker.
- Ligand-receptor enrichment to direct physical communication.
- Marker expression to definitive cell identity.
- Correlation to mechanism.

## Layer 6: Anonymous Human-Relative Ranking

For each task, the evaluator combines rendered human analysis results with the
rendered results from evaluated model-harness conditions. Candidates receive
random identifiers, use the same HVU presentation, and are ranked without
source identity.

Ranking criteria:

- alignment with the scientific question;
- appropriateness of the selected methods for the data;
- traceability from execution and artifacts to observations;
- handling of uncertainty, robustness, and plausible alternatives;
- proportionality of conclusions to the available evidence.

Judges rank scientific quality, not perceived human authorship. Source identity
is revealed only after judgments are fixed. Pairwise judgments may be aggregated
with Bradley-Terry or Plackett-Luce models. Reports should include judge
agreement, task-level uncertainty, human-relative preference, and
baseline-agent-relative preference.

Automated fixed-prompt judges support reproducible development evaluation. Their
rankings require calibration against an independent expert subset before they
serve as an official scientific comparison.

## Score Report Groups

`score_report.json` should group metrics into:

- descriptive.
- schema metrics.
- execution metrics.
- coupling metrics.
- reference alignment.
- claim metrics.
- anonymous ranking and human-relative comparison.

## Context Metrics

First-pass context metrics should use values reliably extractable from logs:

- Total input tokens.
- Total output tokens.
- Total tokens.
- Context Load Ratio.
- Trace Compression Ratio.
- Context Efficiency.

If a harness does not expose token usage, the value should be recorded as
missing rather than estimated.

## Interpretation Boundary

Schema, artifact, and coupling metrics establish compliance and evidence
integrity. They do not by themselves establish overall scientific quality.
Anonymous ranking is the primary comparative endpoint for open-ended tasks, but
it estimates relative preference under a specified task set, anchor pool,
renderer, and judge configuration. It is not an absolute correctness score and
does not make the human candidate ground truth.

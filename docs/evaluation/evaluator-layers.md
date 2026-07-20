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

## Layer 4: Reference Alignment

Reference alignment does not require exact path matching. It compares agent
HVUs, execution subchains, and claims against reference chokepoints, acceptable
method families, and claim surfaces.

Supported matcher classes may include rule-based matching, controlled vocabulary
matching, embedding similarity, fixed-rubric LLM judging, and expert audit
subsets. LLM judging must be auditable and must not become the only primary
score.

Metrics:

- Critical Chokepoint Recall.
- Chokepoint Precision.
- Chokepoint F1.

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

## Score Report Groups

`score_report.json` should group metrics into:

- descriptive.
- schema metrics.
- execution metrics.
- coupling metrics.
- reference alignment.
- claim metrics.

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

## Companion Ranking

Subjective ranking is a companion evaluation. Annotation packets can support
blind pairwise comparison of scientific chain quality, execution chain quality,
and final report quality. Aggregation may use Bradley-Terry, Elo, majority vote,
or inter-rater agreement.

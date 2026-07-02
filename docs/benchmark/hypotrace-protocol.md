# HypoTrace Protocol

## Hypothesis-Verification Unit

The basic unit of the scientific chain is a Hypothesis-Verification Unit, or HVU.

```text
HVU =
  Question / Hypothesis
  Evidence Need
  Method Intent
  Execution Subchain(s)
  Result
  Biological Conclusion
  Next Question
```

The required distinction is:

```text
Result = computational observation from data
Conclusion = biological inference drawn from the result
```

This distinction is central. Marker co-expression is not definitive cell identity,
association is not causation, and ligand-receptor enrichment is not direct proof
of physical cell communication.

## Submission Layout

All model-harness-conditions submit the same structure:

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

The output protocol is common to all conditions. It must not be a special
advantage of one harness.

## `scientific_chain.jsonl`

Each line is one HVU:

```json
{
  "scientific_unit_id": "S03",
  "unit_type": "hypothesis_verification",
  "parent_units": ["S02"],
  "question_or_hypothesis": "Does cluster 5 represent an exhausted CD8 T-cell state associated with non-response?",
  "evidence_need": [
    "cluster 5 expresses CD8 T-cell markers",
    "cluster 5 expresses exhaustion markers",
    "cluster 5 is enriched in non-responders"
  ],
  "method_intent": [
    "marker expression analysis",
    "cluster-level group association analysis"
  ],
  "execution_subchain_ids": ["E03"],
  "result": {
    "computational_observation": "Cluster 5 expresses CD8E, PDCD1 and CTLA4; its abundance is higher in non-responders.",
    "key_artifacts": ["A11", "A12", "A13"]
  },
  "conclusion": {
    "biological_inference": "Cluster 5 is consistent with an exhausted CD8 T-cell state associated with non-response.",
    "scope": "association within this dataset",
    "not_claimed": ["causality", "clinical predictive validity"]
  },
  "next_question": "Is the exhausted T-cell signal spatially localized or associated with specific tumor regions?"
}
```

## `execution_subchains.jsonl`

Each line is one execution subchain. A scientific unit may link to one or more
execution subchains.

```json
{
  "execution_subchain_id": "E03",
  "linked_scientific_unit_id": "S03",
  "stage_question": "Does cluster 5 represent an exhausted CD8 T-cell state associated with non-response?",
  "execution_goal": "Quantify marker expression and response association for cluster 5.",
  "steps": [
    {
      "step_id": "E03.1",
      "action": "compute marker expression for cluster 5",
      "method": "Scanpy dotplot and mean expression summary",
      "parameters": {"markers": ["CD8E", "PDCD1", "CTLA4"]},
      "code_path": "workspace/scripts/E03_1_marker_expression.py",
      "output_artifacts": ["A11"],
      "status": "success"
    }
  ],
  "result_extraction": {
    "summary": "Cluster 5 is marker-consistent with exhausted CD8 T cells and enriched in non-responders.",
    "key_numbers": {"effect_direction": "NR > R", "q_value": 0.018}
  }
}
```

## `artifacts.jsonl`

```json
{
  "artifact_id": "A12",
  "artifact_type": "table",
  "path": "workspace/tables/cluster5_response_association.csv",
  "created_by": "E03.2",
  "derived_from": ["input_adata"],
  "checksum": "sha256:...",
  "summary": "Cluster 5 abundance comparison between responders and non-responders.",
  "validation_status": "exists_and_readable"
}
```

## `final_claims.json`

```json
{
  "claims": [
    {
      "claim_id": "C03",
      "claim_text": "An exhausted CD8 T-cell-like cluster is associated with non-response.",
      "derived_from_scientific_units": ["S03"],
      "supporting_execution_subchains": ["E03"],
      "supporting_artifacts": ["A11", "A12", "A13"],
      "evidence_vector": {
        "marker_support": 0.83,
        "group_association": 0.91,
        "sample_consistency": 0.78,
        "traceability": 1.0,
        "overclaim_penalty": 0.0
      }
    }
  ]
}
```

Do not use `supported`, `partially supported`, or `refuted` as the primary claim
state. Such labels can be post-processed from an evidence vector.

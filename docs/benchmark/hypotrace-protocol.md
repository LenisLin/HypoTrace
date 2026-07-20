# HypoTrace Protocol

## Hypothesis-Verification Unit

The basic unit of the scientific chain is a Hypothesis-Verification Unit, or HVU.

```text
Study Framing:
  S00 data summary

HVU:
  Hypothesis
  Experiment
  Result
  Conclusion
  Next Hypothesis
```

The required distinction is:

```text
Result = computational observation from data
Conclusion = bounded scientific interpretation drawn from the result
```

This distinction is central. Marker co-expression is not definitive cell identity,
association is not causation, and ligand-receptor enrichment is not direct proof
of physical cell communication. Biological interpretation is appropriate only
when the data, study design, and analysis evidence support it; otherwise use
methodological or descriptive interpretation.

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

`scientific_chain.jsonl` contains one isolated `S00` study-framing record
followed by one or more HVU records:

Use task-specific names and values in completed submissions; do not leave
placeholder markers unresolved. Use integers when counts are known; use `null`
when counts are unresolved.

```jsonl
{"scientific_unit_id":"S00","parent_units":[],"data_summary":{"organism":"<task_organism>","tissue":"<task_tissue_or_context>","data_types":["<data_type>"],"sample_count":null,"spatial_unit_count":null,"sample_structure":["<sample_or_replicate_structure>"],"grouping_variables":["<group_or_condition>"],"metadata_available":["<metadata_field>"],"notes":["<data_limit_or_assumption>"]}}
{"scientific_unit_id":"S01","parent_units":[],"hypothesis":"<feature_or_population> is associated with <region_group_or_outcome>.","experiment":{"summary":"<annotation_or_deconvolution_and_association_or_enrichment_analysis>.","execution_subchain_ids":["E01"]},"result":{"observations":[{"observation":"The analysis produced <named_result_object> showing <task_specific_feature_or_population> with <reported_value_or_statistic> for <task_specific_region_group_or_outcome>.","support":"<named_result_object_or_artifact_locator>","interpretation":"This supports <bounded_descriptive_or_associational_interpretation> within task limits."}]},"conclusion":{"summary":"Within the task data and design limits, the result observations support <bounded_descriptive_or_associational_interpretation>."},"next_hypothesis":"<next_hypothesis_or_null>"}
```

## `execution_subchains.jsonl`

Each line is one execution subchain. Each non-framing HVU should have one
primary execution subchain that reaches the result material for that HVU.

A subchain must contain at least one step, and each step must produce at least
one named output object. Steps that load or create the first object may use an
empty `inputs` array when no upstream object exists.

Do not use execution steps to restate the scientific hypothesis. The scientific
hypothesis lives in `scientific_chain`; `execution_subchains` record ordered
method calls and extracted result material.

Inputs that consume prior outputs should reuse the prior output object ID. The
evaluator may resolve these logical object links across execution subchains.

```jsonl
{"execution_subchain_id":"E01","linked_scientific_unit_id":"S01","steps":[{"step_id":"E01.1","inputs":[{"id":"<input_object_id>","object_content":"<task_input_object_content>","format":"<format>"}],"call":"<actual_loader_or_preprocessing_call>","parameters":{"<key_parameter>":"<value>"},"outputs":[{"id":"<prepared_object_id>","object_content":"<prepared_object_content>","format":"<format>"}],"source_ref":{"type":"workspace_script_or_notebook","locator":"workspace/<script_or_notebook_locator>"}},{"step_id":"E01.2","inputs":[{"id":"<prepared_object_id>","object_content":"<prepared_object_content>","format":"<format>"}],"call":"<actual_analysis_call>","parameters":{"<key_parameter>":"<value>"},"outputs":[{"id":"<named_result_object>","object_content":"<result_object_content>","format":"<table_figure_or_object_format>"}],"source_ref":{"type":"workspace_script_or_notebook","locator":"workspace/<script_or_notebook_locator>"}}],"result_extraction":{"observations":[{"observation":"The ordered route produced <named_result_object> showing <task_specific_feature_or_population> with <reported_value_or_statistic>.","support":"<named_result_object_or_artifact_locator>","interpretation":"The route supports the linked HVU result observation within task limits."}]}}
```

## `artifacts.jsonl`

```jsonl
{"artifact_id":"A01","artifact_type":"<table_figure_log_or_model>","path":"workspace/<subdir>/<task_specific_file>","created_by":"E01.2","derived_from":["<named_result_object>"],"checksum":"sha256:<hash_or_unavailable>","summary":"Artifact containing <task_specific_result_material>.","validation_status":"exists_and_readable"}
```

## `final_claims.json`

```json
{
  "claims": [
    {
      "claim_id": "C01",
      "claim_text": "<bounded_task_specific_scientific_claim>",
      "derived_from_scientific_units": ["S01"],
      "supporting_execution_subchains": ["E01"],
      "supporting_artifacts": ["A01"],
      "evidence_vector": {
        "result_traceability": 0.83,
        "statistical_rigor": 0.78,
        "traceability": 1.0,
        "overclaim_penalty": 0.0
      }
    }
  ]
}
```

Do not use `supported`, `partially supported`, or `refuted` as the primary claim
state. Such labels can be post-processed from an evidence vector.

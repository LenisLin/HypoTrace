# Schema Validation Scope

The JSON Schema files in this directory enforce local record shape for the first
strict validation pass. They do not perform JSONL line handling, cross-file
link checks, artifact path checks, task registry checks, or scientific validity
assessment.

Full validation will be implemented in the schema-validation phase. That work
must add JSONL line validation, cross-file link checks, artifact path checks,
and task registry/NAS bundle checks before these schemas are used for primary
scoring.

The first strict schema pass should validate only fields required for the primary
endpoints:

- `S00` `study_framing` fields.
- HVU IDs and `parent_units`.
- `hypothesis`.
- `experiment.summary`.
- `experiment.execution_subchain_ids`.
- `result.observations[]`.
- observation `observation`, `support`, and `interpretation`.
- `conclusion.summary`.
- `next_hypothesis`.
- execution subchain IDs and linked scientific unit IDs.
- execution step IDs.
- ordered step inputs with `id`, `object_content`, and `format`.
- step call and parameters.
- ordered step outputs with `id`, `object_content`, and `format`.
- `source_ref` as null or a lightweight source locator.
- `result_extraction.observations[]`.
- artifact ID, path, created_by, checksum, and validation status.
- final claim IDs, supporting units, supporting execution subchains, supporting
  artifacts, and evidence vector fields.

JSON Schema should enforce local record shape, ID patterns, non-empty strings,
and non-empty execution subchains. JSONL line validation, cross-line existence checks,
execution step prefix consistency with the enclosing execution subchain ID,
ordering checks, artifact `created_by` resolution, and scientific-to-execution
link resolution belong in the later cross-file validator.

The cross-file validator should also check that:

- each referenced execution subchain resolves back to the same linked scientific
  unit;
- non-framing HVUs have at least one linked execution subchain;
- execution subchains are not reused as generic evidence for unrelated HVUs;
- execution result observations align with the linked HVU result observations;
- downstream input object IDs resolve to prior outputs or declared source
  objects where possible;
- final claims include the direct and upstream scientific units, execution
  subchains, and artifacts needed to support the claim.

Output templates are fill-in skeletons. They are not valid completed
submissions until empty strings and placeholder arrays are replaced with real
submission content.

Fields used only for exploratory metrics should not block schema validity in the
first strict validator.

Do not use the current placeholder schemas to claim that a submission is
scientifically valid or fully compliant. A salvage parser, if added later, is
for diagnostics only and must not replace strict primary validation.

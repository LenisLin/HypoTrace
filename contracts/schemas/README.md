# Schema Placeholders

The JSON Schema files in this directory are engineering scaffold placeholders.
They document the expected schema families and a minimal set of required fields.
They are not complete strict validators.

Strict validation will be implemented in the schema-validation phase. That work
must add JSONL line validation, cross-file link checks, artifact path checks,
and task registry/NAS bundle checks before these schemas are used for primary
scoring.

The first strict schema pass should validate only fields required for the primary
endpoints:

- scientific unit IDs and parent/link fields.
- `result.computational_observation`.
- `result.key_artifacts`.
- `conclusion.biological_inference`.
- `conclusion.scope`.
- `conclusion.not_claimed`.
- execution step IDs, status, parameters, code path, and output artifacts.
- artifact ID, path, created_by, checksum, and validation status.
- final claim IDs, supporting units, supporting execution subchains, supporting
  artifacts, and evidence vector fields.

Fields used only for exploratory metrics should not block schema validity in the
first strict validator.

Do not use the current placeholder schemas to claim that a submission is
scientifically valid or fully compliant. A salvage parser, if added later, is
for diagnostics only and must not replace strict primary validation.

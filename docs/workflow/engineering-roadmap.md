# Engineering Roadmap

This roadmap describes planned engineering work. It does not claim that
unimplemented validators, adapters, metrics, or reports already exist.

## Phase 0: Scaffold And Spec Freeze

Deliverables:

- Repository structure for docs, schemas, skills, templates, examples, and tests.
- Shared `contracts/HYPO_TRACE_SKILL.md`.
- Shared `contracts/output_template/`.
- Toy smoke fixtures for schema and dry-run checks.

Acceptance checks:

- Repository structure is Git-trackable.
- Shared output skill and template are visible to all conditions.
- Dry-run creates the required submission tree.

## Phase 1: Schema Models And Validator

Deliverables:

- Schema model definitions.
- JSON Schema export.
- JSONL parser.
- Submission validator.
- Task registry and NAS bundle validator.
- Partial compliance report.

Acceptance checks:

- `validate-submission` rejects missing required files and malformed JSONL.
- Strict validation is used for primary scoring.
- Salvage parsing is limited to diagnostics.
- Validators do not modify submissions.
- Registry validation distinguishes Git task registry entries from smoke
  fixtures.
- Current `contracts/schemas/` files are placeholders until this phase
  implements strict validation.

## Phase 2: Trace Graph And Objective Metrics

Deliverables:

- Submission-to-trace graph builder.
- Artifact path validation.
- Schema metrics.
- Execution metrics.
- Scientific-execution coupling metrics.
- Basic score report.

Acceptance checks:

- Graph links scientific units, execution subchains, steps, artifacts, and final
  claims.
- Missing artifacts and invalid provenance links are reported.
- Result-conclusion separation can be measured.

## Phase 3: Runner Adapters

Deliverables:

- Dry-run adapter.
- Local shell adapter.
- Codex adapter skeleton.
- Claude Code adapter skeleton.
- OpenCode adapter skeleton.
- Passive log collectors.

Acceptance checks:

- Runner prepares sandbox directories.
- Runner copies only agent-visible inputs.
- Runner collects submissions and logs after completion.
- Runner does not provide real-time format correction.

## Phase 4: Condition Injection

Deliverables:

- Condition A: shared output skill and template only.
- Condition B: Condition A plus easy bio skill.
- Condition C: Condition A plus bioharness access documentation and environment
  config.

Acceptance checks:

- All conditions share the same HypoTrace output protocol.
- B condition does not include executable wrappers or hidden task hints.
- C condition does not auto-fill scientific chains or execution subchains.

## Phase 5: Task Builders

Deliverables:

- Public dataset route builder.
- Benchmark research route builder.
- Bioinformatics tool paper route builder.
- Biomedical analysis paper route builder.
- Curator-editable intermediate outputs.

Acceptance checks:

- Builders produce task manifests, data manifests, and reference anchors.
- Builders follow the shared route workflow: general batch workflow -> small-case
  demo test -> full-scale expansion.
- Scoring logic remains in evaluator code or hidden evaluator material.
- Publication-derived paths are treated as anchors, not unique ground truth.

## Phase 6: Reporting And Ranking Packets

Deliverables:

- JSON score reports.
- CSV metric tables.
- HTML report skeleton.
- Leaderboard export.
- Blind pairwise annotation packet generator.

Acceptance checks:

- Reports separate objective metrics from companion ranking.
- Annotation packets hide condition identity where required.
- Expert or LLM ranking inputs are reproducible and auditable.

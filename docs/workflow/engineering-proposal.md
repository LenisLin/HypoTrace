# Engineering Proposal

## Positioning

HypoTrace is not a new bioinformatics agent and does not reimplement
ChatSpatial, OmicOS, CellVoyager, BioMedAgent, or related execution systems.

The engineering target is:

```text
HypoTrace = task registry entry + NAS task bundle + output skill/template + run harness adapter
  + submission validator + trace evaluator
```

ChatSpatial and OmicOS are optional bioharness substrates. Codex, Claude Code,
OpenCode, and similar systems are model-harnesses under evaluation. HypoTrace
defines the shared scientific trace submission and evaluation layer above them.

## Engineering Objects

- Task registry entries define reviewable prompts, manifests, and NAS locators.
  NAS task bundles hold agent-visible inputs, data mount conventions, and hidden
  reference anchors according to visibility.
- Output skill/template defines the common submission format for all conditions.
- Runner adapters prepare sandboxes, inject condition-specific inputs, launch
  harnesses, collect logs, and collect submissions.
- Validators parse submissions after the run and report schema compliance.
- Evaluators build trace graphs and compute objective trace-level metrics.
- Reporting exports summaries, audit artifacts, leaderboards, and annotation
  packets.

## Design Principles

- The output protocol is a benchmark-wide constraint, not a harness advantage.
- The experimental unit is `model-harness-condition`, not a bare model.
- Validation is post-hoc. The main experiment does not give agents real-time
  repair feedback.
- Bioharness conditions may provide execution capability, but they must not
  auto-fill HypoTrace scientific chains or execution subchains.
- Reference chains are anchors for evaluation, not unique ground-truth
  trajectories.
- The schema should remain light enough for open-ended analysis.

## Non-Goals

- New bioinformatics method library.
- New autonomous agent.
- Real-time validator-assisted repair.
- Deep tool-proxy trace auto-fill.
- Perturbation benchmark.
- Forced reproduction of original paper code paths.
- A single total score based only on LLM judging.
- Primary labels such as supported, partially supported, or refuted without an
  evidence vector.

## Risks And Controls

- Fabricated trace claims: check artifact paths, code paths, created-by links,
  input/output provenance, and workspace file existence.
- Heavy schema burden: keep HVUs concise, use JSONL, require only necessary
  fields, and store long logs as files.
- Inconsistent token logs: record token metrics as missing when harness logs are
  unavailable instead of estimating unreliably.
- Reference leakage: runner copies task prompt, data, shared skill, template, and
  allowed condition files only; evaluator reads hidden references separately.
- Bioharness unfairness: C conditions get tool execution access but no reference
  chain, no auto-filled trace, and no real-time validator feedback.
- LLM judge subjectivity: objective metrics are primary; judge prompts, model
  identities, and sampled expert audits must be auditable when judges are used.

## Fixed Decisions

- Project name: HypoTrace.
- Core structure: scientific chain as an `S00` study-framing record plus HVUs
  with hypothesis, experiment, result observations, conclusion, and next
  hypothesis.
- Output constraint: shared skill, template, and prompt requirement.
- Evaluation timing: post-hoc validation only.
- Conditions: base model-harness, base plus easy bio skill, base plus bioharness.
- Engineering modules: spec, tasks, runner, evaluation, reporting.
- First priority: schema, validator, trace graph, objective metrics, and example
  tasks.

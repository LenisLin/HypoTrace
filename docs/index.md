# Documentation Index

## Overview

- `overview/proposal.md`: project motivation, goals, and contribution boundary.
- `overview/design-method.md`: top-level design navigation for dataset construction and benchmark framework discussions.
- `overview/discussion-framework.md`: working discussion order for task units, reference anchors, dataset construction, contracts, benchmark conditions, evaluation, pilot cases, and scale-up.

## Datasets

- [ST Source Screening Round 1](datasets/st-source-screening-round1.md)
- [Public-Data Research Case Extraction](datasets/public-data-research-case-extraction.md):
  article-anchored public-database research cases and their data-access boundary.
- [Tool / Method Case Extraction](datasets/tool-method-case-extraction.md):
  ST tool/method paper and tutorial screening, source localization, case data
  localization, and handoff to dual-chain extraction.
- [Dual Chain Extraction](datasets/dual-chain-extraction.md): shared dual-chain framework for agent submissions and case-derived curation records.
- `datasets/task-package.md`: task construction and reference anchor design.
- `datasets/task-authoring.md`: task authoring workflow and reference isolation rules.
- `datasets/data-contract.md`: NAS storage and run output contract.

## Benchmark

- `benchmark/benchmark-design.md`: benchmark questions, task levels, conditions, and design boundary.
- `benchmark/experimental-design.md`: A/B/C conditions, controls, and analysis contrasts.
- `benchmark/hypotrace-protocol.md`: submission protocol and hypothesis-verification unit.

## Workflow

- `workflow/engineering-proposal.md`: engineering positioning, modules, non-goals, and risks.
- `workflow/engineering-roadmap.md`: staged implementation plan and acceptance checks.
- `workflow/architecture.md`: repository and runtime layer boundaries.
- `workflow/adapter-contract.md`: runner and model-harness adapter contract.
- `workflow/run-directory.md`: sandbox input, submission, log, eval, and ranking packet layout.

## Evaluation

- `evaluation/evaluation-metrics.md`: objective metrics and companion ranking.
- `evaluation/evaluator-layers.md`: post-hoc evaluator layers and metric outputs.
- `evaluation/scientific-validity.md`: validity, bias, statistics, and overclaim controls.

## Contributor Checklist

- Keep task registry entries and NAS task bundles separate from evaluator logic.
- Use the same `contracts/HYPO_TRACE_SKILL.md` and
  `contracts/output_template/` across all model-harness-conditions.
- Treat reference chains as anchors, not gold trajectories.
- Require agents to submit HypoTrace files rather than only final answers.
- Separate computational results from biological conclusions.
- Record code, parameters, artifacts, and evidence for each claim.
- Avoid causal or clinical claims without appropriate evidence.
- Runner code must not provide real-time format correction to agents.
- Hidden references must not enter the agent workspace.
- Bioharness conditions must not auto-fill HypoTrace scientific chains.
- LLM or expert ranking must not be the only primary score.
- Git `tasks/` entries must not contain hidden references or truth files.
- Experiment configs must not redefine the shared submission contract.
- Task sets select tasks; they do not duplicate task bundles.
- Complete task bundles live under NAS `tasks/<task_id>/`.

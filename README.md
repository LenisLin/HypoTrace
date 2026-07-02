# HypoTrace

HypoTrace is a benchmark protocol for evaluating bioinformatics agents through
hypothesis-to-evidence traces. Instead of scoring only final answers or
unconstrained trajectories, HypoTrace requires each agent to submit a structured
scientific chain. Each scientific unit follows a hypothesis-verification
structure: question or hypothesis, evidence need, method intent, execution
subchain, result, biological conclusion, and next question.

The goal is to evaluate whether an agent can convert biological data analysis
into evidence-grounded scientific conclusions. HypoTrace is not a new
bioinformatics harness or method library. It is a common output and evaluation
protocol applied uniformly to different model-harness conditions, including base
coding agents, base agents with lightweight bioinformatics skills, and base
agents equipped with state-aware bioharnesses such as ChatSpatial or OmicOS.

## Repository Roots

- Code root: `/home/lenislin/Experiment/projects/HypoTrace`
- Data root: `/mnt/NAS_21T/ProjectData/HypoTrace_Data`

The code repository stores protocol definitions, contract assets, documentation,
experiment specifications, and lightweight task registry entries. Complete task
bundles, hidden references, runtime outputs, trajectories, and large data live
under the NAS data root.

## Documentation

Start with:

- `docs/index.md`
- `docs/overview/proposal.md`
- `docs/overview/design-method.md`

Topic areas:

- `docs/datasets/task-package.md`
- `docs/datasets/task-authoring.md`
- `docs/datasets/data-contract.md`
- `docs/benchmark/benchmark-design.md`
- `docs/benchmark/experimental-design.md`
- `docs/benchmark/hypotrace-protocol.md`
- `docs/workflow/engineering-proposal.md`
- `docs/workflow/engineering-roadmap.md`
- `docs/workflow/architecture.md`
- `docs/workflow/adapter-contract.md`
- `docs/workflow/run-directory.md`
- `docs/evaluation/evaluation-metrics.md`
- `docs/evaluation/evaluator-layers.md`
- `docs/evaluation/scientific-validity.md`

## Layout

```text
hypotrace/         Python package for task loading, runners, graders, evaluation, reporting
contracts/         Hard contracts, output templates, schemas, prompt/skill templates, config templates
experiments/       Experiment packages with task sets and run-specific configs
tasks/             Lightweight Git task registry entries, not full task bundles
configs/           Deprecated top-level pointer; real configs live under experiments or contracts
scripts/           CLI wrappers for data preparation, runs, validation, and reports
docs/              Themed design documentation for overview, datasets, benchmark, workflow, and evaluation
examples/          Toy task and dry-run examples
tests/             Contract tests for the protocol skeleton
```

`contracts/HYPO_TRACE_SKILL.md` and `contracts/output_template/` are the
canonical shared output controls for all conditions. `contracts/skills/` is
reserved for condition-specific templates and does not replace the shared output
skill.

## Initial Verification

```bash
python -m pytest tests
```

# HypoTrace

HypoTrace is being developed as an executable scientific-agent evaluation
harness for open-ended bioinformatics analysis. Its benchmark suites are
designed as versioned workloads that provide scientific questions, task data,
runtime conditions, human analysis anchors, baseline-agent runs, and evaluator
configurations. The harness defines a common execution and evidence-capture
boundary so that different agents can choose different valid methods while
remaining comparable.

Instead of scoring only final answers or treating one extracted analysis as the
required path, HypoTrace represents each completed analysis as a structured
scientific chain. Each chain contains an `S00` study-framing record followed by
hypothesis-verification units with a hypothesis, verification experiment, linked
execution subchain, result, bounded scientific conclusion, and optional next
hypothesis.

The goal is to evaluate whether an agent can convert biological data analysis
into evidence-grounded scientific conclusions under a shared runtime and output
contract. Human and agent analyses can be anonymized and ranked together for
scientific quality; human choices are comparison anchors, not ground-truth
answers. HypoTrace is not a general bioinformatics tool library or a replacement
for execution substrates such as ChatSpatial or OmicOS. Those systems, base
coding agents, and agents with lightweight bioinformatics skills are conditions
that can run inside the HypoTrace evaluation harness.

## Repository Roots

- Code root: `/home/lenislin/Experiment/projects/HypoTrace`
- Data root: `/mnt/NAS_21T/ProjectData/HypoTrace_Data`

The code repository stores protocol definitions, contract assets, documentation,
experiment specifications, and lightweight task registry entries. Complete task
bundles, hidden references, runtime outputs, trajectories, and large data live
under the NAS data root.

## Current ST Tool/Method Curation Snapshot

As of 2026-07-15, the ST tool/method corpus contains 140 method sources and 964
screened cases. Of these, 424 cases are `DATA_READY` and included in the active
dual-chain set; 540 cases are `BLOCKED_EXTERNAL` and retained only for curation
provenance or later repair. All 424 active cases have validated readable NAS
paths and a confirmed active chain.

The corpus is stored under:

```text
/mnt/NAS_21T/ProjectData/HypoTrace_Data/raw_data/tool_method/
  <method_slug>/
    screen/screening.yaml
    source/
    cases/<case_id>/
      case_screen.yaml
      source_manifest.yaml
      data/
        case_data_manifest.yaml
        objects/
        samples/
      dual_chain/<chain_id>/
        chain_manifest.yaml
        scientific_chain.jsonl
        execution_subchains.jsonl
        independent_check.md
```

The mutable queues and aggregate state are maintained under
`raw_data/tool_method/_registry_batches/layer1_tier_a_140/`. In particular,
`human_review/stage2_case_review_queue.md`, `stage3/stage3_queue.md`, and
`stage4/stage4_chain_queue.md` are the authoritative current indexes. Historical
chain directories may remain on NAS as provenance even when a case is not in
the active queue.

## Current STOmicsDB Public-Data Snapshot

The active STOmicsDB public-data research scope is frozen to 16 STDS records.
The authoritative ordered allowlist is defined in
`docs/datasets/public-data-research-case-extraction.md`. STOmicsDB intake,
dispatch, case construction, and downstream extraction must use only that
allowlist.

## Documentation

Start with:

- `docs/index.md`
- `docs/overview/proposal.md`
- `docs/overview/design-method.md`
- `docs/overview/discussion-framework.md`

Topic areas:

- `docs/datasets/task-package.md`
- `docs/datasets/task-authoring.md`
- `docs/datasets/data-contract.md`
- `docs/datasets/stomicsdb-localization-workflow.md`
- `docs/datasets/stomicsdb-case-construction-workflow.md`
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

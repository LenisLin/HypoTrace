# HypoTrace Proposal

## Working Title

HypoTrace: Benchmarking Bioinformatics Agents through Hypothesis-to-Evidence Traces

Alternative titles:

HypoTrace: Evaluating Bioinformatics Agents by Scientific Trace Quality

HypoTrace: An Executable Evaluation Harness for Open-Ended Bioinformatics Agents

The project name should remain HypoTrace. The core structure is not two parallel
chains. It is a scientific chain organized around hypothesis verification, with
one or more execution subchains bound to each scientific unit.

## One-Sentence Definition

HypoTrace is an executable evaluation harness for open-ended bioinformatics
agents. Versioned benchmark suites run within the harness. It evaluates whether
an agent can turn biological data analysis into traceable, auditable, and
comparable scientific conclusions using a structured path:

```text
S00 study framing + HVU: hypothesis -> experiment -> result observations -> conclusion -> next hypothesis
```

HypoTrace is not a new tool library or an analysis bioharness. Its contribution
is the shared runtime, trace, and evaluation boundary that turns open-ended
bioinformatics research into a hypothesis-to-evidence trace where scientific
conclusions bind to data, methods, code, parameters, results, and artifacts.
Agents remain free to choose different scientifically defensible methods.

## Motivation

Existing bio-agent evaluations often emphasize pipeline completion, single-tool
omics tasks, final-answer claim recovery, or agent-system tooling. These are
important but do not fully answer whether an agent's biological conclusion is
supported by an explicit and inspectable evidence bridge.

Bioinformatics failures are often chain failures. An agent may run clustering but
misinterpret a cluster, draw a differential expression plot but write association
as causation, or identify markers without checking sample consistency, cell-type
composition, or clinical association. HypoTrace makes these failures visible by
requiring every scientific progress node to expose the study framing,
hypothesis, verification experiment, linked execution subchain, result
observations, bounded conclusion, and next hypothesis.

## Existing Benchmark Boundary

The relevant benchmark landscape does not support the broad claim that existing
bio-agent benchmarks lack data or evaluation standards. Existing benchmarks
evaluate different, partially overlapping constructs:

- answer or claim recovery;
- code generation and successful execution;
- recovery of a local numerical or biological result;
- end-to-end pipeline completion;
- scientific support for a conclusion.

These constructs are not interchangeable. A correct final answer does not by
itself establish that the agent accessed the intended data, executed a valid
analysis, produced inspectable artifacts, or drew a conclusion within the scope
of its results. Conversely, a benchmark may validly test code execution or local
result recovery without attempting to evaluate an open-ended scientific
argument.

The following comparison records the public contracts of representative
benchmarks as reviewed on 2026-07-27. It is a scope comparison, not a quality
ranking.

| Benchmark | Public task and evaluation contract | Boundary relevant to HypoTrace |
|---|---|---|
| [BixBench](https://github.com/Future-House/BixBench) | Provides heterogeneous input-data capsules, an empty notebook in a containerized environment, and agent execution through Python, R, and Bash. Open answers are primarily graded against reference answers by a judge model; MCQ evaluation is also supported. | Demonstrates data-interactive analysis and final-answer recovery, but its primary score does not require a standardized data-to-artifact-to-conclusion evidence path. |
| [ScienceAgentBench](https://github.com/OSU-NLP-Group/ScienceAgentBench) | Requires a self-contained Python program and evaluates generated programs, execution results, and cost using task datasets, evaluation programs, reference programs, rubrics, and a containerized harness. Its maintainers later released a verified split to reduce false-negative grading. | Directly evaluates executability, while also showing that task solvability and evaluator correctness require independent validation. It does not make open-ended biological conclusion support its common output unit. |
| [SpatialBench](https://github.com/latchbio/spatialbench) | Uses analysis-state snapshots, structured answers, and deterministic grader families for numeric values, choices, marker sets, label sets, and distributions. A representative sample and trajectories are public, while the full set is withheld and many data objects are addressed through `latch://` nodes. | Provides strong local-result evaluation. Official evaluability and third-party reproducibility remain distinct when data and hidden cases are platform-hosted. |
| [BioAgent Bench](https://github.com/bioagent-bench/bioagent-bench) | Provides task prompts, download definitions for input, reference, and result files, and per-task pipeline reproduction scripts. Its public documentation cautions that result or truth files should not be assumed correct unless explicitly validated. | Supplies executable task ingredients, but heterogeneous reference outputs still require task-specific validation before they can serve as a common scientific evaluation standard. |
| [BioDSA-1K](https://huggingface.co/datasets/zifeng-ai/BioDSA-1K) | Publishes hypotheses, study metadata, labels, cBioPortal dataset mappings, and dataset schemas. Data access is represented partly through external dataset identifiers and URLs rather than only through benchmark-local snapshots. | Tests hypothesis validation with real data sources, but reproducible execution depends on fixing source identity, retrieval scope, and data visibility when external resources are used. |

This comparison also distinguishes three meanings of "data not provided":

1. Hidden data are mounted during an official evaluation. This can support a
   contamination-resistant centralized benchmark, although independent
   reproduction is limited unless an equivalent access route is available.
2. Data acquisition is part of the task. This can validly test resource discovery
   and intake, but the benchmark must fix the source identifier, version or
   generation, expected file scope, access policy, and failure behavior.
3. No task data, executable environment, or runtime artifact is available. Such
   a task can evaluate answer recovery or analysis planning, but it cannot by
   itself establish empirical execution.

## Executable Scientific Evidence

For HypoTrace, an execution claim requires more than generated code or a plausible
answer. The minimum evidence path is:

```text
identified task data
  -> runtime-successful execution with recorded methods and parameters
  -> readable, schema-valid artifacts
  -> result observations derived from those artifacts
  -> bounded conclusions linked to the result observations
```

The evaluator should therefore keep several judgments separate:

- **task solvability**: the specified data are visible and the requested analysis
  is feasible under the declared resource and access policy;
- **execution validity**: the relevant code ran successfully and declared outputs
  satisfy their artifact contracts;
- **analytical validity**: the selected method is appropriate for the question
  and data, and key outputs satisfy applicable task-specific invariants or
  tolerances;
- **scientific validity**: each substantive conclusion is supported by linked
  results and artifacts, distinguishes observation from interpretation, and does
  not overstate the study design;
- **reproducibility and leakage control**: task data and references are bound to
  the intended generation, while hidden answers and source trajectories are not
  exposed to the evaluated agent.
- **human-relative scientific quality**: anonymized human and agent analyses are
  ranked under the same scientific-quality criteria, with source identities
  revealed only after ranking.

Open-ended analyses need not reproduce a publication's unique method path or
wording. Reference analyses should act as non-exclusive anchors. A valid
alternative analysis may pass when its execution is auditable, its critical
logic is adequate, and its conclusion remains compatible with the evidence.
Case-derived HVU chains record observed human analysis choices; they are not
answer labels, mandatory chokepoints, or ground-truth trajectories.

## HypoTrace Position

HypoTrace does not claim to be the first benchmark to provide data, execute agent
code, or grade scientific results. Its target is a harness-level joint evaluation
boundary that remains incompletely covered when these properties are scored
separately:

```text
data -> execution -> artifact -> result -> bounded scientific conclusion
                                               |
                          anonymized human/agent scientific-quality ranking
```

The intended contribution is a harness-first, benchmark-backed system for this
boundary. Objective checks establish trace and execution integrity. Anonymous
human/agent ranking compares overall scientific quality without making a human
path the answer key. Reference or chokepoint alignment remains diagnostic and
must not penalize a valid alternative analysis solely because it differs from a
publication route. This positioning is narrower than a claim that prior
benchmarks are not executable, and it identifies the additional evidence needed
to interpret successful execution as scientific support.

## Core Questions

- Can open-ended bioinformatics analysis be represented as a scoreable
  scientific trace without forcing a single path?
- Under the same output protocol, where do easy bio skills and bioharnesses
  improve performance?
- Does trace quality provide more diagnostic information than final-answer-only
  scores?
- Can anonymized human and agent HVU chains support stable scientific-quality
  ranking when analysts choose different valid methods?
- How does scientific chain length affect agent behavior?
- Can publication-derived scientific chains serve as non-exclusive references
  rather than ground truth?

## Objectives

1. Define a common HypoTrace submission protocol for all agents.
2. Define a unified task registry and NAS bundle pattern for public dataset,
   benchmark research, bioinformatics tool paper, and biomedical analysis paper
   sources.
3. Build trace-level integrity metrics and an anonymized human-relative ranking
   protocol for scientific quality, execution quality, result-conclusion
   separation, evidence-backed claims, overclaiming, and context efficiency.
4. Compare base model-harness pairs, base pairs with easy bio skills, and base
   pairs with bioharness substrates under the same output protocol.

## Expected Contributions

- A hypothesis-to-evidence output protocol.
- An executable scientific-agent evaluation harness.
- A unified task construction framework.
- Trace-level integrity metrics and anonymized human-relative ranking.
- A controlled comparison design for model ability, prompt knowledge, and
  execution substrate contributions.

## Non-Claims

HypoTrace is not a new bioinformatics tool ecosystem, does not claim broader
method coverage than ChatSpatial or OmicOS, does not extract hidden
chain-of-thought, does not treat publication paths or human choices as ground
truth, does not equate human-likeness with scientific validity, does not use
real-time validation in the main experiment, and does not use subjective LLM
judging as the only evaluation standard.

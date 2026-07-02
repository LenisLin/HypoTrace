# HypoTrace Proposal

## Working Title

HypoTrace: Benchmarking Bioinformatics Agents through Hypothesis-to-Evidence Traces

Alternative title:

HypoTrace: Evaluating Bioinformatics Agents by Scientific Trace Quality

The project name should remain HypoTrace. The core structure is not two parallel
chains. It is a scientific chain organized around hypothesis verification, with
one or more execution subchains bound to each scientific unit.

## One-Sentence Definition

HypoTrace is a benchmark protocol for bioinformatics agents. It evaluates whether
an agent can turn open-ended biological data analysis into traceable, auditable,
and comparable scientific conclusions using a structured path:

```text
question/hypothesis -> method intent -> execution subchain -> result -> biological conclusion
```

HypoTrace is not a new tool library or a new bioharness. Its contribution is to
turn open-ended bioinformatics research into a hypothesis-to-evidence trace where
scientific conclusions must bind to data, methods, code, parameters, results, and
artifacts.

## Motivation

Existing bio-agent evaluations often emphasize pipeline completion, single-tool
omics tasks, final-answer claim recovery, or agent-system tooling. These are
important but do not fully answer whether an agent's biological conclusion is
supported by an explicit and inspectable evidence bridge.

Bioinformatics failures are often chain failures. An agent may run clustering but
misinterpret a cluster, draw a differential expression plot but write association
as causation, or identify markers without checking sample consistency, cell-type
composition, or clinical association. HypoTrace makes these failures visible by
requiring every scientific progress node to expose the question, evidence need,
method intent, execution, result, conclusion, and next question.

## Core Questions

- Can open-ended bioinformatics analysis be represented as a scoreable
  scientific trace without forcing a single path?
- Under the same output protocol, where do easy bio skills and bioharnesses
  improve performance?
- Does trace quality provide more diagnostic information than final-answer-only
  scores?
- How does scientific chain length affect agent behavior?
- Can publication-derived scientific chains serve as non-exclusive references
  rather than ground truth?

## Objectives

1. Define a common HypoTrace submission protocol for all agents.
2. Define a unified task registry and NAS bundle pattern for public dataset,
   benchmark research, bioinformatics tool paper, and biomedical analysis paper
   sources.
3. Build trace-level evaluation metrics for scientific chain quality, execution
   quality, result-conclusion separation, evidence-backed claims, chokepoints,
   overclaiming, and context efficiency.
4. Compare base model-harness pairs, base pairs with easy bio skills, and base
   pairs with bioharness substrates under the same output protocol.

## Expected Contributions

- A hypothesis-to-evidence output protocol.
- A unified task construction framework.
- Trace-level scientific evaluation metrics.
- A controlled comparison design for model ability, prompt knowledge, and
  execution substrate contributions.

## Non-Claims

HypoTrace is not a new bioinformatics tool ecosystem, does not claim broader
method coverage than ChatSpatial or OmicOS, does not extract hidden
chain-of-thought, does not treat publication paths as unique ground truth, does
not use real-time validation in the main experiment, and does not use subjective
LLM judging as the only evaluation standard.

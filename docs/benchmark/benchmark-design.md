# Benchmark Design

HypoTrace is a trace-constrained scientific evaluation layer. It evaluates
whether bioinformatics agents can transform open-ended data analysis into
auditable scientific conclusions without forcing a single analysis path.

## Scientific Questions

1. Can open-ended bioinformatics analysis be structured as a scoreable
   scientific trace?
2. Under a shared output protocol, where does a bioharness improve performance?
3. Does scientific trace quality provide more diagnostic information than
   final-answer-only scoring?
4. How does scientific chain length affect agent behavior?
5. Can publication-derived reference chains serve as anchors rather than unique
   ground truth?

## Conditions

The experiment unit is `model-harness-condition`.

- A: base model/harness plus HypoTrace output.
- B: base model/harness plus easy bio skill plus HypoTrace output.
- C: base model/harness plus bioharness substrate plus HypoTrace output.

All conditions use the same selected task, budgets, resource policy, hidden
references, and post-hoc evaluator.

## Task Levels

- Level 1: single-method task. Use for schema smoke tests, tool invocation sanity
  checks, and artifact validation.
- Level 2: analysis episode. Use for multi-step tasks with two to five
  hypothesis-verification units.
- Level 3: open research question. Use for long scientific chains with multiple
  defensible conclusions and higher overclaim risk.

HypoTrace focuses on Level 2 and Level 3 tasks. Data source is orthogonal to
chain length and can be public dataset, benchmark research, bioinformatics tool
paper, or biomedical analysis paper.

## Design Lineage

HypoTrace uses configuration-driven execution and postprocessing patterns from
BixBench, task registry and downloader separation patterns from BioAgent Bench,
and Python toolkit documentation and test organization patterns from SpatialBench.
Its scientific focus differs from all three: it evaluates result-to-conclusion
evidence quality, not only pipeline completion or final answer matching.

## Non-Claims

HypoTrace is not a new bioinformatics tool ecosystem, does not claim broader
method coverage than ChatSpatial or OmicOS, does not extract hidden
chain-of-thought, does not treat publication paths as unique truth, does not use
a real-time validator in the main experiment, and does not make subjective LLM
judging the sole evaluation standard.

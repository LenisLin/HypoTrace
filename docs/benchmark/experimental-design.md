# Experimental Design

The experimental unit is `model-harness-condition`, not a bare model.

Examples:

```text
GPT / Codex / A
Claude / Claude Code / B
GLM / OpenCode / A
DeepSeek / OpenCode / A
```

## Conditions

- A: base model-harness pair.
- B: A plus easy bio skill.
- C: A plus bioharness substrate such as ChatSpatial or OmicOS.

All conditions must use the same HypoTrace output protocol.

## Controls

Fix the following across conditions:

- same selected task.
- same HypoTrace output protocol.
- same `contracts/HYPO_TRACE_SKILL.md`.
- same `contracts/output_template/`.
- same resource budget.
- same walltime.
- same maximum turns.
- same maximum tokens.
- same package environment where possible.
- same network policy.
- same post-hoc evaluator.
- same hidden reference material.

The main experiment should not use a real-time validator that prompts agents to
repair missing fields. Format failures should count as schema failure or partial
compliance.

Condition B easy bio skills may add method names, links, best-practice checks,
and common pitfalls. They must not replace or modify the shared HypoTrace output
skill or output template.

## Bias And Attribution Controls

The experiment can compare `model-harness-condition` units. It should not claim
that observed differences isolate the model, tool substrate, prompt knowledge, or
bioharness implementation unless the design explicitly controls those factors.

Required controls:

- Stratify tasks by level, modality, source route, and expected analysis family.
- Randomize or counterbalance run order across conditions.
- Use paired comparisons within the same selected task whenever possible.
- Audit condition inputs before runs to confirm that B and C do not receive
  hidden references, scoring rubrics, or task-specific hints.
- Record missing logs, failed runs, and schema failures as outcomes, not as
  silent exclusions.
- Report Level 2 and Level 3 results separately before aggregate summaries.

## Contrasts

A to B asks whether lightweight method guidance improves planning. Primary
signals: method appropriateness, HVU completeness, chokepoint recall, and final
claim compatibility.

B to C asks whether a bioharness provides execution advantage beyond prompt
guidance. Primary signals: execution completion, artifact validity, code
provenance, parameter recording, and scientific-execution linkage.

A to C asks whether state-aware or schema-enforced bioharness support improves
overall scientific trace quality. Primary signals: evidence-backed claim rate,
final claim compatibility, overclaim rate, context efficiency, and expert
ranking.

## Task Scale Analysis

Report Level 2 and Level 3 separately.

- Level 2 should expose execution quality differences more clearly.
- Level 3 should expose scientific chain quality, overclaim rate, and context
  efficiency differences more clearly.

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

## Human-Relative Comparison Unit

For each selected task, the comparison pool contains one or more human analysis
results and the completed results from evaluated model-harness conditions. Human
results are candidates in the pool, not answer keys. All candidates are rendered
through the same HVU view, assigned random identifiers, and ranked without source
identity.

Ranking judges assess scientific quality rather than whether a result appears
human-authored. The ranking criteria should cover question alignment, method-data
fit, evidence traceability, robustness to plausible alternatives, and conclusion
scope. Tool names, parameters, observations, and scientific limitations remain
visible because they are material to quality assessment; author, model, harness,
paper, and stylistic source cues are removed when they are not scientifically
necessary.

Source identities are revealed only after ranking. Human-relative performance is
then estimated from pairwise preference probabilities or latent ranking scores.
A published case-derived human chain supports comparison with a published human
analysis choice. A claim of same-condition human equivalence additionally
requires a calibration subset in which human analysts receive the same question,
data visibility, environment, and resource policy as the agents.

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
- same anonymization renderer and ranking criteria.

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
- Randomize candidate identifiers and presentation order for each judge.
- Keep source identity hidden until every ranking decision is fixed.
- Measure judge agreement and retain disagreements rather than silently
  collapsing them into a single label.

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

## Ranking Analysis

Use pairwise ranking when the candidate pool is too large for reliable complete
ordering. Bradley-Terry or Plackett-Luce aggregation may estimate task-local
latent quality. Report human-relative and baseline-agent-relative preference
probabilities with uncertainty aggregated by task; do not treat all pairwise
comparisons from one task as independent samples.

Automated judge prompts can provide reproducible development scores when the
prompt, judge model, anchor pool, and renderer are versioned. Official scientific
comparisons require calibration against an independent expert-ranked subset.
Ranking does not establish absolute scientific correctness, and human-relative
preference does not imply that every human analysis choice is valid.

## Task Scale Analysis

Report Level 2 and Level 3 separately.

- Level 2 should expose execution quality differences more clearly.
- Level 3 should expose scientific chain quality, overclaim rate, and context
  efficiency differences more clearly.

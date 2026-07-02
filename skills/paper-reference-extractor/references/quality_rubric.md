# Reference Chain Quality Rubric

| Dimension | Points | Criteria |
| --- | ---: | --- |
| Chain question design | 20 | Chain questions are explicit, non-overlapping, and connected by dependency. |
| Intermediate step grain | 20 | Steps are neither algorithm-only fragments nor whole-paper summaries. |
| Logic continuity | 20 | `previous_finding -> decision_rationale -> logic_gain -> next_decision` forms a readable progression. |
| Evidence fidelity | 20 | Evidence is anchored to the paper and does not invent methods, results, or accessions. |
| Boundary control | 10 | Result, interpretation, gap, and overclaim boundary are separated. |
| Main-path purity | 10 | Non-computational article context does not pollute the reusable analysis path. |

Grade:

- `A`: 85-100, suitable as hidden/evaluator reference.
- `B`: 70-84, usable after expert review.
- `C`: 50-69, draft only.
- `D`: below 50, re-extract.

Automatic validators only check structure. Scientific quality still requires human review.

## Required Manual Checks

| Check | Fail Condition |
| --- | --- |
| Data readiness | Public/restricted/processed-only data status is absent or overstated. |
| Evidence anchor | A main-chain step lacks paper/PDF/figure/table/source anchor. |
| Evidence/result boundary | `observed_evidence` contains biological conclusion instead of reported data facts. |
| Interpretation boundary | Co-localization, enrichment, correlation, network prediction, or ligand-receptor inference is written as causality. |
| Main-path purity | Wet-lab, animal, clinical, drug-delivery, or other non-computational validation becomes a connected main-chain step. |
| Hidden-reference boundary | Reference chain, rubric, or curator notes are copied into agent-facing prompt or public task registry. |

## Case Promotion Rule

A registry candidate can become a hidden reference only after:

1. Data route is checked and recorded as `reusable_data_ready` or explicitly accepted as `data_link_but_needs_auth`.
2. The PDF/methods/results are extracted into JSONL with anchors.
3. `validate_reference_chain.py` passes.
4. A human reviewer scores the chain at `A` or a high-confidence `B`.
5. The full reference files are stored in evaluator-only / NAS bundle, not in agent-visible material.

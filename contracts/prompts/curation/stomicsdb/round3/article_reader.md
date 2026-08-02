# STOmicsDB Round 3 Article Reader

## Purpose

Read one assigned dataset-local article completely and return an ordered,
article-faithful inventory of its in-scope Results. This role supplies fixed
source evidence to the dataset worker.

## Assignment

Receive:

```yaml
article_reading_assignment:
  stds_id:
  repository_workdir: /home/lenislin/Experiment/projects/HypoTrace
  article_manifest_path:
  article_pdf_path:
```

The two article paths must resolve to:

```text
<assigned dataset directory>/article/article_manifest.yaml
<assigned dataset directory>/article/article.pdf
```

## References

Read only:

- `AGENTS.md`
- `docs/datasets/stomicsdb-case-construction-workflow.md`, limited to article
  binding, complete article reading, result enumeration, and source-evidence
  boundaries
- the assigned `article_manifest.yaml`
- the assigned `article.pdf`

Use the article manifest for identity and the complete PDF for scientific
content. Standard PDF text extraction and page rendering may be used as direct
reading methods.

## Work

1. Confirm that the manifest and PDF identify the same article and belong to the
   assigned STDS dataset.
2. Read the complete article for scientific context, including the relationship
   among the introduction, methods, Results sections, main-text figures, and
   discussion.
3. Build the structured result inventory from every Results section and the
   main-article figures, tables, and stable text passages used by those Results.
4. Keep supplementary-only analyses outside the structured Round 3 result
   inventory.
5. Traverse Results in article order and assign stable `R01`, `R02`, ... before
   any downstream filtering.
6. Treat one result as one bounded Results-section scientific question,
   conclusion, one or more main-article source anchors, and ordered analysis
   route.
7. Record `result_section` using the article's readable section or subsection
   label. Record a nonempty `source_anchors` list. Each entry has exactly
   `type: figure | table | text` and a stable `locator` such as a main-text
   figure or panel label, table label, or Results heading plus bounded text
   locator.
8. State `scientific_question` as the question evaluated by that result rather
   than as the observed answer.
9. State `conclusion` as the bounded article-reported result, including null,
   non-significant, or unfavorable findings when present.
10. Express `analysis_steps` in scientific order. Every step contains one
    article-supported `input -> method -> output` transition.
11. Split steps when the article clearly describes distinct analytical
    transitions. Keep a single step when greater granularity is not supported by
    the article.
12. Preserve the article's uncertainty and claim strength. Correlation,
    association, descriptive localization, prediction, and causal inference
    remain distinct.
13. Complete the full in-scope inventory before returning.

The structured response contains only the source evidence needed by the dataset
worker. Spatial-input classification, canonical-data inspection,
representation equivalence, sample mapping, auxiliary-resource necessity, data
support, candidate construction, and case acceptance belong to the dataset
worker.

The response has no experimental-design field, exhaustive locator ledger,
supplementary inventory, mapping grade, coverage grade, candidate decision, or
data-readiness decision.

## Return

Return exactly:

```yaml
article_results:
  status: complete | failed
  stds_id:
  article_path:
  article_title:
  results:
    - result_id: R01
      result_section:
      source_anchors:
        - type: figure | table | text
          locator:
      scientific_question:
      conclusion:
      analysis_steps:
        - input:
          method:
          output:
  failure_reason:
```

For `complete`, the STDS ID matches the assignment; `article_path` is
NAS-data-root-relative; title and article identity agree; every in-scope Results
unit is present in article order; each result has a question, conclusion, at
least one article anchor, and at least one ordered analysis step; and
`failure_reason` is `null`.

The returned result objects are exactly field-compatible with
`source_manifest.results`; the worker copies them without field translation.

Use `failed` when article identity cannot be confirmed, the PDF is unreadable,
or the complete in-scope Results inventory cannot be produced. A failed response
uses `results: []` and gives a specific `failure_reason`; partial extraction is
not returned as `complete`.

## Fixed boundaries

This leaf role completes the assigned article reading directly and returns to
the dataset worker. It writes no files, starts no subagents, searches no external
resource, and makes no downstream spatial, data-support, candidate, or review
decision.

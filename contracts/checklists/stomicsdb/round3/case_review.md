# STOmicsDB Round 3 Case Review Checklist

This checklist is the sole authority for Round 3 review checks and response
shape. Review both candidate-bearing and `no_candidate` proposals. Apply every
common check in round 1; apply formal three-file checks only when
`proposed_status: accepted`. In round 2, check repaired targets and directly
affected references only.

## Response

Return exactly:

```yaml
case_review:
  stds_id:
  review_round: 1 | 2
  checked_targets: []
  issues:
    - area: coverage | decision | output | localization | logic
      target:
      finding:
      required_change:
```

An empty `issues` list is the only acceptance signal. Each issue names one
concrete target, states the observed nonconformity, and requests the minimum
worker repair. The reviewer never returns rewritten decisions or manifests.

## Round 1 Common Checks

Apply these checks to both proposal types:

1. The proposal uses the assigned `stds_id` and
   `proposed_status: accepted | no_candidate`.
2. Perform one bounded coverage scan of the main article's Results headings and
   associated main-article figure, table, and stable text anchors. Every
   in-scope unit is present in the fixed article-reader inventory, in article
   order, with exactly one stable `Rxx`. Supplementary-only analyses remain
   excluded.
3. The proposal has exactly one `result_decisions` entry for every fixed reader
   `Rxx`, no duplicate or foreign ID, and no renumbering.
4. Every `uses_assigned_spatial_data` value is `yes | no | uncertain` and its
   `spatial_basis` is supported by the fixed article and assigned-data evidence.
5. Every decision accurately states the necessary `required_inputs`, mapped
   `local_data_ids`, auxiliary requests, and bounded `support_basis`.
6. `input_support: supported | unsupported | not_evaluated` follows from the
   fixed inspection and resource evidence. `not_evaluated` is not used for a
   spatial-use `yes` result whose required inputs were evaluated.
7. `candidate_eligible` occurs if and only if spatial use is `yes` and input
   support is `supported`; every excluded decision has a valid reason.
8. `not_located` remains temporary resource evidence, makes each affected
   result unsupported, and is not converted to formal `Axx`.
9. Favorable direction, significance, or result reproduction is not used as an
   eligibility or support condition; null and unfavorable results are treated
   under the same input rules.
10. Every eligible `Rxx` closes to exactly one candidate in an accepted
    proposal. No excluded `Rxx` appears in a candidate.
11. `no_candidate` is valid exactly when zero decisions are eligible. Its three
    draft outputs are null. It has completed the same coverage and decision
    review and cannot bypass review.
12. `accepted` is valid only with at least one eligible result and non-null
    source, data, and case draft objects. Apply all checks below.

An omitted in-scope reader result is reported as a coverage issue. Do not add or
assign an `Rxx`; the omission is nonrepairable in the current window.

## Candidate-Bearing Formal Checks

### Output And Provenance

13. The drafts contain exactly the three top-level objects in the output
    contract and no additional formal file.
14. The assignment and all three objects use the same assigned `stds_id`.
15. `source_manifest_path` and `case_data_manifest_path` have the exact fixed
    relative values.
16. Every formal record contains exactly its required contract fields. There is
    no top-level `Dxx.format` or obsolete flat `data_ids` field.
17. `Rxx`, `Dxx`, `Axx`, and `Cxx` IDs have the correct prefixes and are unique
    in their classes.
18. Every cross-file result, data, auxiliary-resource, order, and connection
    reference resolves to the correct class.
19. Every formal `Rxx`, `Dxx`, and `Axx` is used by at least one final candidate;
    unsupported and unused working records are absent.
20. Formal output excludes process hashes and process history, but includes all
    required upstream article, article-manifest, dataset-manifest,
    source-manifest, samples, files, localization, and component-file hashes.
21. Each required hash is a raw-byte SHA-256 matching the fixed evidence; each
    required generation ID matches its bound upstream manifest.

### Source

22. `article_path` and `article_manifest_path` are NAS-data-root-relative and
    resolve to the assigned dataset-local pair; their hashes, generation ID,
    title, and identity agree.
23. Every formal result is a fixed eligible reader result and preserves its
    original `Rxx`, question, conclusion, ordered analysis steps, and claim
    strength.
24. Every result has a nonempty main-article `source_anchors` list. Each entry is
    exactly `type: figure | table | text` plus a stable `locator`; no
    supplementary-only anchor is used.

### Dataset And Components

25. `dataset_binding` contains the exact assigned dataset manifest, source
    manifest, samples, and files paths, hashes, and required generation IDs.
26. Each `Dxx.path` is the narrowest canonical root for one coherent logical
    dataset, not a component file or arbitrary common ancestor. Its
    `data_context` contains exactly `organism`, `tissue_or_context`,
    `spatial_assay`, `sample_summary`, and `available_metadata`.
27. Every `Dxx.localization_bindings` entry resolves to a parsed assigned
    `localization.yaml`; path, hash, and generation ID match fixed evidence.
28. Every component is null or has component-file entries with exact
    NAS-data-root-relative path, format, and SHA-256 plus a bounded summary.
29. Every component file is declared by a bound localization record, exists,
    is readable, stays within the assigned dataset, and matches its hash.
30. Component summaries are limited to representation, relevant sample
    coverage, joins or alignment, and minimum observed schema.
31. Components grouped in a `Dxx` have compatible assay identity and sample
    coverage; expression-coordinate and image alignment is stated when needed.
32. Every referenced sample ID resolves through the bound `samples.jsonl` and
    agrees with component coverage and the fixed inspection evidence.

### Inputs And Resources

33. Every formal result has exactly one `result_data_links` record containing
    `data_inputs` and `auxiliary_resource_ids`.
34. Every data input has one valid `Dxx`, one permitted input role, exact
    relevant sample IDs, and all components required by that analysis.
35. Each `required_components[].paths` list is a subset of the corresponding
    referenced `Dxx` component's `files[].path` values; no required path is
    absent, unreadable, or inferred.
36. Every `Axx` is necessary to at least one retained result, reproduces fixed
    resource evidence, uses one of the three formal access classifications, and
    has `local_availability: absent`. No `not_located` record is persisted.
37. Admission support remains distinct from execution availability. A formal
    absent `Axx` can support Round 3 admission but does not assert downstream
    `DATA_READY`.

### Candidate Logic

38. Each candidate's `result_order` contains exactly its result IDs once, in
    article order; every one-result candidate has no connection.
39. For every candidate member, collect `data_inputs` with
    `input_role: primary_spatial`. All members declare the same nonempty `Dxx`
    set, and candidate `spatial_data_ids` equals that set exactly.
40. Every multi-result connection refers only to members, matches corresponding
    analysis-step output and input text, preserves compatible assay/sample
    scope, represents a real downstream dependency, and is acyclic.
41. Independent results remain separate even if they occur in the same article
    or use related data.
42. Candidate auxiliary-resource IDs equal resources used by member-result
    links, and all candidate-local input IDs occur through those links.

## Round 2 Checks

Check every repaired target against its corresponding rule and check only
directly affected references. Preserve round-1 conclusions for unchanged
evidence and content. A new issue is valid only when a round-2 edit created or
exposed it in a changed target or direct dependency. Return all remaining
issues together. An empty issue list accepts the revised proposal; no third
round is available.

# STOmicsDB Round 3 Case Reviewer

## Purpose

Perform lightweight, evidence-bounded review of one Round 3 proposal with
`proposed_status: accepted | no_candidate`. The reviewer checks bounded article
coverage, review-only decisions, conditional output shape, localization, and
scientific logic against fixed evidence. It reports defects only. The dataset
worker owns every repair and every file write.

One reviewer context handles at most two rounds for the assigned STDS dataset.

## Assignment

Receive round 1:

```yaml
case_review_assignment:
  stds_id:
  repository_workdir: /home/lenislin/Experiment/projects/HypoTrace
  nas_data_root: /mnt/NAS_21T/ProjectData/HypoTrace_Data
  dataset_directory:
  review_round: 1
  checklist_path: contracts/checklists/stomicsdb/round3/case_review.md
  output_template_path: contracts/output_template/stomicsdb/round3/case_outputs.md
  proposed_status: accepted | no_candidate
  result_decisions: []
  draft_outputs:
    source_manifest:
    case_data_manifest:
    case_manifest:
  article_results:
  inspected_data:
  resource_access:
  changed_targets: [all_proposal_targets]
```

For `no_candidate`, each draft output is null. `resource_access` is null when no
auxiliary-resource search was required.

The worker may send one same-context follow-up:

```yaml
case_review_revision:
  stds_id:
  review_round: 2
  proposed_status: accepted | no_candidate
  revised_result_decisions: []
  revised_draft_outputs:
    source_manifest:
    case_data_manifest:
    case_manifest:
  revised_inspected_data:
  repaired_issue_targets: []
  changed_targets: []
```

## References

Read only `AGENTS.md`, the assigned checklist and output contract, and the fixed
evidence and proposal supplied in the assignment. The checklist owns checks and
response shape. The output contract owns accepted formal fields.

## Work

### Round 1

1. Confirm the assigned STDS identity across the assignment, fixed evidence,
   proposal, and any non-null drafts.
2. Perform only a bounded scan of main-article Results headings and their
   figure, table, and stable text anchors. Compare that scan with the fixed
   ordered article-reader inventory. Do not independently re-extract the
   article or broaden supplementary scope.
3. If an in-scope result is omitted, report the omission as a coverage defect.
   Do not add or assign an `Rxx`; the worker will treat reader inventory omission
   as nonrepairable in this window.
4. Apply every common checklist item to `result_decisions` and the proposed
   status. Review `no_candidate` with the same coverage and decision checks as
   `accepted`.
5. Apply the formal three-file checks only to `proposed_status: accepted` with
   non-null drafts. Confirm that `no_candidate` drafts are null.
6. Use supplied article, inspected-data, and resource-access records as the
   fixed evidence base. When a decision cannot otherwise be made, open only a
   declared source anchor or already referenced canonical component.
7. Return all current issues together, one minimum requested worker repair per
   concrete target.

An empty round-1 issue list accepts either proposal type.

### Round 2

1. Confirm the same assignment and fixed article-reader and resource-access
   evidence.
2. Review every repaired decision or draft target and its directly affected
   references. If status changed, apply the corresponding conditional proposal
   checks.
3. Accept revised inspection only when a round-1 issue required a more precise
   read of an already referenced component, within the same result, `Dxx`,
   assay, sample, and component scope.
4. Preserve round-1 conclusions for unchanged content. Add a new issue only
   when a round-2 edit created or exposed it in a changed target or direct
   dependency.
5. Return all remaining issues together.

An empty round-2 issue list accepts the revised proposal. Any remaining issue
is final. The reviewer handles no third round.

### Evidence stability and ownership

The reviewer never adds or renumbers an `Rxx`, discovers a new resource, adds a
logical dataset, expands sample coverage, creates candidate scope, edits a
decision, repairs a manifest, or writes a file. A targeted reread may clarify a
finding only. The worker alone repairs every reported defect.

Distinguish article fidelity from scientific truth, provenance linkage from
analysis-input support, Round 3 admission support from execution availability,
unavailable access from unnecessariness, and null or unfavorable findings from
unsupported findings.

## Return

Return exactly the response in
`contracts/checklists/stomicsdb/round3/case_review.md`. Do not add a pass/fail
field, narrative report, rewritten object, or process history. An empty issue
list is the only acceptance signal.

## Fixed boundaries

The reviewer writes no Git or NAS file, starts no subagent, searches no network,
executes no analysis, and performs no independent whole-article extraction or
broad canonical-data discovery. It reports defects; the worker owns repairs.

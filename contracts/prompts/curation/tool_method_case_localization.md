# Tool/Method Case Localization Curator Prompt

## Purpose

Use this internal prompt to localize source material and case data for one
specified ST tool/method case before dual-chain extraction.

## Required References

Read these project documents before acting:

- `docs/datasets/tool-method-case-extraction.md`
- `docs/datasets/data-contract.md`
- `docs/datasets/dual-chain-extraction.md`

## Inputs

- `method_screening_yaml`:
  `raw_data/tool_method/<method_slug>/screen/screening.yaml`.
- `method_slug`.
- `case_id`.
- NAS data root.

## Outputs

Write curator-facing outputs under the NAS data root:

- `raw_data/tool_method/<method_slug>/cases/<case_id>/case_screen.yaml`
- `raw_data/tool_method/<method_slug>/cases/<case_id>/source_manifest.yaml`
- `raw_data/tool_method/<method_slug>/cases/<case_id>/data/case_data_manifest.yaml`
- `raw_data/tool_method/<method_slug>/cases/<case_id>/data/objects/<data_object_id>/`
- `raw_data/tool_method/<method_slug>/cases/<case_id>/data/samples/<sample_id>/`

## Workflow

1. Read the method-level screen.
2. Select exactly one matching `cases[]` entry by `case_id`; stop if there is
   no match or more than one match.
3. Write the selected `screening.yaml:cases[case_id]` entry to
   `raw_data/tool_method/<method_slug>/cases/<case_id>/case_screen.yaml`.
4. Read screen-stage source local paths from `screening.yaml:sources`, data
   leads from the specified case entry, and classify the case by `case_depth`
   and source type.
5. For an article-derived case, ensure the source set includes the original
   paper PDF, extracted article text, and exact case-bearing material such as
   supplement, data availability, figure/table source, notebook, script, or
   repository file.
6. If the method-level screen did not localize article PDF/text for an
   article-derived case, localize them in the current case dispatch and record
   them in `source_manifest.yaml`. For an official tutorial case, localize the
   exact tutorial source and any exact notebook, script, vignette, or example
   used by the case.
7. Continue to data localization only after the current `source_manifest.yaml`
   records the case source set.
8. Inspect same-method `DATA_READY case_data_manifest.yaml` records for
   reusable artifacts from matching `dataset_group_id` or `related_case_ids`.
   Candidate reused manifests must parse before reuse.
9. Resolve data by route type from the specified case entry and localized
   source material: direct download, accession, portal/index, repository
   directory/path, package/helper route, existing NAS path, or notebook-derived
   lead.
10. Before assigning `BLOCKED_EXTERNAL`, resolve repairable routes: after a
   failed public route, perform one targeted online re-resolution using
   accession, DOI data availability, portal study ID, sample IDs, or file
   names; if an exact derived artifact is unavailable but localized source
   material gives raw public data routes and construction logic, resolve the
   raw route and prepare a source-supported equivalent object. Record the
   rebuild route in existing fields; this is data preparation, not dual-chain
   extraction.
11. For each required reachable concrete artifact, retrieve, copy, or localize
   artifacts under the current case's `data/objects/<data_object_id>/` or
   `data/samples/<sample_id>/` path when the object is not already usable
   through Case-reference reuse.
12. Continue retrieval repair for reachable incomplete downloads, including
   resumable retrieval or redownload when practical.
13. Unpack, extract, prepare, load, or inspect archives/native containers in
    the case-local data tree when needed.
14. Read or inspect local artifacts enough to support Stage 3, and record
    shape, identifiers, coordinate semantics, sample structure, retrieval
    attempts, local artifacts, read summary, remaining issues, and usable
    partial artifacts in `case_data_manifest.yaml`.
15. When Case-reference reuse applies, create a soft link in the current case's
    `data/` tree and record `reused_from_case_id`, link path, and target path
    in the current `case_data_manifest.yaml` using YAML-safe free text.
16. Set final `case_data_manifest.data_localization_status` to `DATA_READY` or
    `BLOCKED_EXTERNAL`.
17. Before ending the dispatch, parse `case_screen.yaml`,
    `source_manifest.yaml`, and `case_data_manifest.yaml`; repair only YAML
    scalar formatting if needed. Confirm final
    `case_data_manifest.data_localization_status` is `DATA_READY` or
    `BLOCKED_EXTERNAL` and `case_data_manifest.data_objects[].visibility` uses
    only `agent_input_candidate`, `evaluator_context_only`, or
    `excluded_derived_output`.

Use `DATA_READY` when required local artifacts have been read and
`case_data_manifest.yaml` records local paths, prepared format when applicable,
read summary, coordinate semantics, sample structure, identifier checks, and
remaining issues. Use `BLOCKED_EXTERNAL` only when the next required action
truly requires access, credentials, unavailable service, storage, or no public
route after targeted re-resolution. `DATA_REPAIR_REQUIRED` is an internal
repair-loop condition and must continue the localization work rather than end
the stage.

## Subagent Dispatch

Use `contracts/prompts/curation/dispatch_tool_method_case_localization.md` when
assigning this stage to a subagent. The dispatch prompt points back to this
file as the mandatory stage protocol.

## Boundary

Stop before writing `chain_manifest.yaml`, `scientific_chain.jsonl`, or `execution_subchains.jsonl`.

# Tool/Method Case Screening Curator Prompt

## Purpose

Use this internal prompt to produce one method-level `screening.yaml` from a
method or article seed. The screen enumerates all source-level ST tool/method
cases before any case-specific data localization or dual-chain extraction.

## Required References

Read these project documents before acting:

- `docs/datasets/tool-method-case-extraction.md`
- `docs/datasets/data-contract.md`

## Inputs

- Method slug.
- Method name when available.
- Article title, DOI, URL, implementation repository, documentation URL, or
  tutorial/example seed when available.
- NAS data root.

## Workflow

1. Start from the method/article seed and search online for the method article,
   implementation repository, official documentation, tutorials, vignettes,
   examples, and notebooks.
2. Localize source material needed for case extraction under
   `raw_data/tool_method/<method_slug>/source/`.
3. Record package-level source acquisition in
   `raw_data/tool_method/<method_slug>/source/source_manifest.yaml`.
4. Record source URL, local path, role, format, and notes in
   `screening.yaml:sources`.
5. Extract all source-level ST tool/method cases into `cases[]`, keyed by
   `case_id`.
6. Apply the weak data lead rule for article cases: include an article case
   when there is an ST application source locator and usable data leads, even if
   file-level artifacts are unresolved.
7. Treat implementation-package vignettes, examples, and documentation as
   `official_tutorial`. For RCTD, `spacexr` vignettes, examples, and
   documentation count as official tutorial sources.
8. Retain article and tutorial cases using the same dataset as separate cases,
   and assign a shared `dataset_group_id` or fill `related_case_ids` when the
   shared dataset relationship is identifiable.
9. Fill `coverage_notes` with included and skipped article sections,
   tutorials, scripts, vignettes, examples, and reasons.

## Output

Write these screening-stage outputs:

- `raw_data/tool_method/<method_slug>/screen/screening.yaml`
- `raw_data/tool_method/<method_slug>/source/source_manifest.yaml`
- Source files under
  `raw_data/tool_method/<method_slug>/source/`

The output must be method-level and include `sources`, `coverage_notes`, and
`cases[]`. `screening.yaml:sources` must reference the screening-stage source
files that were localized for case extraction. `screening.yaml:cases[]` is the
full downstream localization queue; priority, initial validation notes, or
recommended order must not reduce Stage 2 coverage.

## Boundary

Screening-stage outputs are limited to the method-level `screening.yaml`,
package-level `source/source_manifest.yaml`, and screening-stage source files.
Raw data localization, `case_screen.yaml`, per-case `source_manifest.yaml`,
`case_data_manifest.yaml`, chain artifacts, and independent-check artifacts are
produced by later stages. Avoid wording such as "selected for Stage 2" as a
limiting instruction. Paper conclusions are recorded as source information
rather than ground truth.

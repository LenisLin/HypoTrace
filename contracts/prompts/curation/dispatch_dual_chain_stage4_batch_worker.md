# Dispatch: Dual-Chain Stage 4 Batch Worker

This is an orchestration wrapper for running independent confirmation over a
queue of existing chain directories. It is not a new stage protocol.

## Required Inputs

- `batch_id` or `stage4_queue_id`
- Stage 4 chain queue rows.
- NAS data root: `/mnt/NAS_21T/ProjectData/HypoTrace_Data`.

Each queue row should include `method_slug`, `case_id`, `chain_id`, and
`chain_dir`.

## Required References

Read these project documents and prompts before acting:

- `docs/datasets/tool-method-case-extraction.md`
- `docs/datasets/data-contract.md`
- `docs/datasets/dual-chain-extraction.md`
- `contracts/prompts/curation/dual_chain_independent_check.md`
- `contracts/prompts/curation/dispatch_dual_chain_independent_check.md`

## Mandatory Protocol

Use `dual_chain_independent_check.md` and
`dispatch_dual_chain_independent_check.md` for each chain directory. This
wrapper only orchestrates a queue of chain-level checks.

## Batch Workflow

1. Require one unique queue row per `method_slug`, `case_id`, `chain_id`, and
   `chain_dir`.
2. Resolve `chain_dir` under the configured NAS tool/method root and require the
   three Stage 3 chain files before dispatch.
3. In resume mode, dispatch rows whose `independent_check.status` is
   `not_started`. Skip terminal rows unless the caller explicitly requests a
   recheck.
4. Process each row independently. A dispatch interruption does not change that
   chain's manifest and does not stop later rows.
5. Retry one interrupted dispatch once. Do not retry a completed Stage 4
   decision automatically.
6. After each completed dispatch, reparse `chain_manifest.yaml`, require
   `independent_check.md`, require a terminal independent-check status, and
   verify the corresponding `chain_status` mapping.

## Boundary

Do not edit Stage 1/2 manifests, create new chains, or edit
`scientific_chain.jsonl` or `execution_subchains.jsonl`. Write only the Stage 4
outputs allowed by the independent-check prompt.

## Required Response

Report chain count processed, confirmed count, needs-revision count, blocked
count, and one row per non-confirmed chain with the main issue and suggested
human repair target.

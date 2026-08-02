# Dispatch: Dual-Chain Stage 4 Batch Worker

This is an orchestration wrapper for running independent confirmation over a
queue of existing chain directories. It is not a new stage protocol.

## Required Inputs

- `batch_id` or `stage4_queue_id`
- Stage 4 chain queue rows.
- NAS data root: `/mnt/NAS_21T/ProjectData/HypoTrace_Data`.

Each queue row includes `case_route`, `case_id`, `chain_id`, absolute final
chain path, unique absolute extraction-attempt staging path, and unique absolute
review-attempt staging path. A `tool_method` row also includes `method_slug`.
A `public_database_stomicsdb` row instead includes `stds_id`, `candidate_id`,
absolute `case_manifest.yaml`, `source_manifest.yaml`, and
`data/case_data_manifest.yaml` paths, and the deterministic public-data
`chain_id`. Child assignments contain these values inline; a queue path does
not replace the assignment.

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

1. Require one unique route-aware queue row per `case_id`, `chain_id`, and
   final chain path. Recompute and verify public-data deterministic chain IDs.
2. Resolve the final chain path under the route-appropriate configured NAS root
   and require the three nonempty Stage 3 chain files before dispatch. Require
   unique NAS review staging for this attempt.
3. In resume mode, dispatch rows whose `independent_check.status` is
   `not_started`. Skip terminal rows unless the caller explicitly requests a
   recheck.
4. Process each row independently. A dispatch interruption does not change that
   chain's manifest and does not stop later rows.
5. Retry one interrupted dispatch once. Do not retry a completed Stage 4
   decision automatically.
6. The leaf writes only a proposed full `chain_manifest.yaml` and
   `independent_check.md` in review staging.
7. Acquire the chain lock, reopen final and proposed files, verify both final
   JSONL raw-byte hashes are unchanged, and validate the proposal. Without
   releasing the lock, publish with a recoverable per-chain replacement
   transaction: `PREPARED`, backup of current final review-owned files,
   install and verify, then `COMMITTED`; restore and verify the backup and
   record `ROLLED_BACK` on failure.
8. After a committed dispatch, reparse final `chain_manifest.yaml`, require
   final `independent_check.md`, require a terminal independent-check status,
   verify the corresponding `chain_status` mapping, and reconfirm unchanged
   JSONL hashes.

## Boundary

Do not edit Stage 1/2 manifests, create new chains, or edit
`scientific_chain.jsonl` or `execution_subchains.jsonl`. A
`needs_revision` result records findings only. Any extraction replacement is
a new complete three-file Stage 3 attempt and separate locked recoverable
transaction with a complete prior-chain backup and
`independent_check.status: not_started`.

## Required Response

Report chain count processed, confirmed count, needs-revision count, blocked
count, and one row per non-confirmed chain with the main issue and suggested
human repair target.

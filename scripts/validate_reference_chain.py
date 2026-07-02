#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate publication-derived reference analysis logic chain JSONL."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


REQUIRED = {
    "schema_version",
    "paper_id",
    "paper_title",
    "source_pdf",
    "paper_domain",
    "assay_types",
    "chain_id",
    "chain_title",
    "chain_question",
    "chain_question_short",
    "chain_order",
    "depends_on_chain_ids",
    "step_id",
    "step_order",
    "step_title",
    "step_question",
    "connects_from",
    "connects_to",
    "analysis_scope",
    "task_grain",
    "step_origin",
    "evidence_level",
    "gold_confidence",
    "data_input",
    "previous_finding",
    "decision_rationale",
    "method_or_analysis",
    "what_it_tests",
    "article_explicit_operations",
    "likely_default_processing",
    "observed_evidence",
    "analysis_result",
    "biological_interpretation",
    "logic_gain",
    "next_decision",
    "remaining_gap",
    "interpretation_boundary",
    "evidence_support",
    "review_flags",
    "article_context_after_analysis",
}

STEP_ORIGINS = {"explicit_method", "explicit_result", "inferred_default", "mixed"}
EVIDENCE_LEVELS = {
    "preprocessing",
    "association",
    "enrichment",
    "spatial_mapping",
    "network_support",
    "candidate_prioritization",
    "context_validation",
}
CONFIDENCE = {"high", "medium", "low"}
SCHEMA_VERSION = "analysis_logic_chain"


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {line_number}: invalid JSON: {exc}") from exc
    if not rows:
        raise ValueError("no records")
    return rows


def check_item(item: dict) -> None:
    missing = REQUIRED - set(item)
    if missing:
        raise ValueError(f"{item.get('step_id', '<unknown>')}: missing {sorted(missing)}")
    if item["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"{item['step_id']}: invalid schema_version {item['schema_version']}")
    if item["analysis_scope"] != "agent_executable_data_analysis":
        raise ValueError(f"{item['step_id']}: invalid analysis_scope")
    if item["task_grain"] != "intermediate":
        raise ValueError(f"{item['step_id']}: invalid task_grain")
    if item["step_origin"] not in STEP_ORIGINS:
        raise ValueError(f"{item['step_id']}: invalid step_origin {item['step_origin']}")
    if item["evidence_level"] not in EVIDENCE_LEVELS:
        raise ValueError(f"{item['step_id']}: invalid evidence_level {item['evidence_level']}")
    if item["gold_confidence"] not in CONFIDENCE:
        raise ValueError(f"{item['step_id']}: invalid gold_confidence {item['gold_confidence']}")
    for field in ["chain_question", "step_question", "decision_rationale", "method_or_analysis", "observed_evidence", "analysis_result", "logic_gain", "next_decision", "interpretation_boundary", "evidence_support"]:
        if item.get(field) in (None, "", []):
            raise ValueError(f"{item['step_id']}: empty {field}")
    if not isinstance(item["evidence_support"], list) or not item["evidence_support"]:
        raise ValueError(f"{item['step_id']}: evidence_support must be a non-empty list")
    for support in item["evidence_support"]:
        if not isinstance(support, dict):
            raise ValueError(f"{item['step_id']}: evidence_support entries must be objects")
        if not support.get("anchor_text") or not support.get("evidence_summary"):
            raise ValueError(f"{item['step_id']}: evidence_support missing anchor_text or evidence_summary")


def check_connections(rows: list[dict]) -> None:
    by_chain = defaultdict(list)
    seen_step_ids = set()
    for item in rows:
        if item["step_id"] in seen_step_ids:
            raise ValueError(f"duplicate step_id {item['step_id']}")
        seen_step_ids.add(item["step_id"])
        by_chain[item["chain_id"]].append(item)
    for chain_id, items in by_chain.items():
        items.sort(key=lambda x: x["step_order"])
        orders = [item["step_order"] for item in items]
        if orders != list(range(1, len(items) + 1)):
            raise ValueError(f"{chain_id}: non-continuous step_order {orders}")
        for index, item in enumerate(items):
            expected_from = items[index - 1]["step_id"] if index else None
            expected_to = items[index + 1]["step_id"] if index < len(items) - 1 else None
            if item["connects_from"] != expected_from:
                raise ValueError(f"{item['step_id']}: connects_from should be {expected_from}")
            if item["connects_to"] != expected_to:
                raise ValueError(f"{item['step_id']}: connects_to should be {expected_to}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", type=Path)
    args = parser.parse_args()
    rows = read_jsonl(args.jsonl)
    for item in rows:
        check_item(item)
    check_connections(rows)
    print(f"OK: {args.jsonl} ({len(rows)} records)")


if __name__ == "__main__":
    main()

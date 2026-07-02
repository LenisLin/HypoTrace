#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export Analysis Logic Chain JSONL to HypoTrace reference draft files."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


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
        raise ValueError("JSONL contains no records")
    return rows


def common_metadata(rows: list[dict]) -> dict:
    first = rows[0]
    return {
        "paper_id": first.get("paper_id"),
        "paper_title": first.get("paper_title"),
        "source_pdf": first.get("source_pdf"),
        "schema_version": first.get("schema_version"),
        "reference_visibility": "evaluator_only",
        "reference_only_not_ground_truth": True,
        "agent_visible": False,
    }


def reference_scientific_chain(rows: list[dict]) -> dict:
    return {
        "metadata": common_metadata(rows),
        "reference_units": [
            {
                "unit_id": row["step_id"],
                "chain_id": row["chain_id"],
                "question_or_hypothesis": row["step_question"],
                "evidence_need": [row["what_it_tests"]],
                "acceptable_method_families": [row["method_or_analysis"]],
                "reference_result": row["analysis_result"],
                "reference_conclusion": row["biological_interpretation"],
                "next_question": row["next_decision"],
                "uncertainties": [row["interpretation_boundary"]],
                "source_anchors": row["evidence_support"],
                "reference_only_not_ground_truth": True,
            }
            for row in rows
        ]
    }


def reference_claim_surface(rows: list[dict]) -> dict:
    by_chain = defaultdict(list)
    for row in rows:
        by_chain[row["chain_id"]].append(row)
    claims = []
    for chain_id, items in by_chain.items():
        items.sort(key=lambda x: x["step_order"])
        claims.append(
            {
                "claim_id": f"{chain_id}_CLAIM",
                "claim_text": items[-1]["biological_interpretation"],
                "required_evidence_types": sorted({item["evidence_level"] for item in items}),
                "acceptable_alternative_claims": [],
                "forbidden_overclaims": [item["interpretation_boundary"] for item in items if item.get("interpretation_boundary")],
                "supporting_reference_units": [item["step_id"] for item in items],
                "evidence_summary": items[-1]["analysis_result"],
                "limitations": [items[-1]["interpretation_boundary"]],
                "reference_only_not_ground_truth": True,
            }
        )
    return {"metadata": common_metadata(rows), "reference_claims": claims}


def reference_execution_chain(rows: list[dict]) -> dict:
    return {
        "metadata": common_metadata(rows),
        "reference_execution_units": [
            {
                "unit_id": f"RE_{row['step_id']}",
                "execution_unit_id": f"RE_{row['step_id']}",
                "linked_reference_unit_id": row["step_id"],
                "method_family": row["evidence_level"],
                "original_method": row["method_or_analysis"],
                "acceptable_alternatives": [],
                "method_intent": row["method_or_analysis"],
                "input_data": row["data_input"],
                "paper_explicit_operations": row["article_explicit_operations"],
                "likely_default_processing": row["likely_default_processing"],
                "expected_observations": row["observed_evidence"],
                "reference_only_not_required_exact_path": True,
            }
            for row in rows
        ]
    }


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    rows = read_jsonl(args.jsonl)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.out_dir / "reference_scientific_chain.json", reference_scientific_chain(rows))
    write_json(args.out_dir / "reference_claim_surface.json", reference_claim_surface(rows))
    write_json(args.out_dir / "reference_execution_chain.json", reference_execution_chain(rows))
    print(f"Wrote HypoTrace reference drafts to {args.out_dir}")


if __name__ == "__main__":
    main()

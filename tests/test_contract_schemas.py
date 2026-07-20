import json
from pathlib import Path

import jsonschema
import pytest


def test_scientific_chain_schema_rejects_unfilled_hvu_template() -> None:
    schema = _load_json("contracts/schemas/scientific_chain.schema.json")
    template_records = _load_jsonl("contracts/output_template/scientific_chain.jsonl")

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(template_records[1], schema)


def test_scientific_chain_schema_accepts_study_framing_with_sample_structure() -> None:
    schema = _load_json("contracts/schemas/scientific_chain.schema.json")
    record = {
        "scientific_unit_id": "S00",
        "parent_units": [],
        "data_summary": {
            "organism": "mouse",
            "tissue": "brain",
            "data_types": ["spatial transcriptomics"],
            "sample_count": 2,
            "spatial_unit_count": 100,
            "sample_structure": ["two sections from one animal"],
            "grouping_variables": ["region"],
            "metadata_available": ["sample_id"],
            "notes": ["example framing record"],
        },
    }

    jsonschema.validate(record, schema)


def test_scientific_chain_schema_accepts_direct_hvu_execution_link() -> None:
    schema = _load_json("contracts/schemas/scientific_chain.schema.json")
    record = {
        "scientific_unit_id": "S01",
        "parent_units": [],
        "hypothesis": "Marker expression is associated with region A.",
        "experiment": {
            "summary": "Annotation and association analysis test regional marker support.",
            "execution_subchain_ids": ["E01"],
        },
        "result": {
            "observations": [
                {
                    "observation": "Marker expression was higher in region A.",
                    "support": "marker_region_table",
                    "interpretation": "This supports a bounded regional association.",
                }
            ]
        },
        "conclusion": {
            "summary": "The result supports a bounded regional association."
        },
        "next_hypothesis": None,
    }

    jsonschema.validate(record, schema)


def test_scientific_chain_schema_rejects_obsolete_flat_hvu_fields() -> None:
    schema = _load_json("contracts/schemas/scientific_chain.schema.json")
    record = {
        "scientific_unit_id": "S01",
        "parent_units": [],
        "hypothesis": "Marker expression is associated with region A.",
        "experiment": {
            "summary": "Association analysis tests marker support.",
            "execution_subchain_ids": ["E01"],
        },
        "result": {
            "observations": [
                {
                    "observation": "Marker expression was higher in region A.",
                    "support": "marker_region_table",
                    "interpretation": "This supports a bounded regional association.",
                }
            ]
        },
        "conclusion": {
            "summary": "The result supports a bounded regional association."
        },
        "next_hypothesis": None,
        "execution_subchain_ids": ["E01"],
    }

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(record, schema)


def test_execution_subchain_schema_accepts_observation_result_extraction() -> None:
    schema = _load_json("contracts/schemas/execution_subchains.schema.json")
    record = {
        "execution_subchain_id": "E01",
        "linked_scientific_unit_id": "S01",
        "steps": [
            {
                "step_id": "E01.1",
                "inputs": [],
                "call": "load_marker_region_table",
                "parameters": {},
                "outputs": [
                    {
                        "id": "marker_region_table",
                        "object_content": "marker expression by region",
                        "format": "table",
                    }
                ],
                "source_ref": {"type": "workspace_script", "locator": "workspace/scripts/run.py"},
            }
        ],
        "result_extraction": {
            "observations": [
                {
                    "observation": "Marker expression was higher in region A.",
                    "support": "marker_region_table",
                    "interpretation": "The route supports the linked HVU observation.",
                }
            ]
        },
    }

    jsonschema.validate(record, schema)


def test_execution_subchain_schema_rejects_unfilled_step_template() -> None:
    schema = _load_json("contracts/schemas/execution_subchains.schema.json")
    template_record = _load_jsonl("contracts/output_template/execution_subchains.jsonl")[0]

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(template_record, schema)


def test_artifact_schema_rejects_unfilled_artifact_template() -> None:
    schema = _load_json("contracts/schemas/artifacts.schema.json")
    template_record = _load_jsonl("contracts/output_template/artifacts.jsonl")[0]

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(template_record, schema)


def _load_json(path: str) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_jsonl(path: str) -> list[object]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

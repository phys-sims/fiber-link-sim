from __future__ import annotations

import json
from pathlib import Path

from fiber_link_sim.data_models.spec_models import (
    get_simulation_result_schema,
    get_simulation_spec_schema,
)

SCHEMA_DIR = Path("src/fiber_link_sim/schema")


def _load_schema(path: Path) -> dict:
    return json.loads(path.read_text())


def _normalize_schema(schema: dict) -> dict:
    normalized = dict(schema)
    normalized.pop("$schema", None)
    normalized.pop("$id", None)
    return normalized


def test_simulation_spec_schema_alignment() -> None:
    expected = _normalize_schema(get_simulation_spec_schema())
    actual = _normalize_schema(_load_schema(SCHEMA_DIR / "simulation_spec.schema.v0.3.json"))
    assert expected == actual


def test_simulation_result_schema_alignment() -> None:
    expected = _normalize_schema(get_simulation_result_schema())
    actual = _normalize_schema(_load_schema(SCHEMA_DIR / "simulation_result.schema.v0.3.json"))
    assert expected == actual

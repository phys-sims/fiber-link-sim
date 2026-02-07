from __future__ import annotations

import json
from importlib import resources


def test_schema_resources_available() -> None:
    base = resources.files("fiber_link_sim") / "schema"
    spec_path = base / "simulation_spec.schema.v0.2.json"
    result_path = base / "simulation_result.schema.v0.1.json"

    assert spec_path.is_file()
    assert result_path.is_file()
    json.loads(spec_path.read_text())
    json.loads(result_path.read_text())


def test_example_resources_available() -> None:
    example_path = (
        resources.files("fiber_link_sim") / "schema" / "examples" / "qpsk_longhaul_1span.json"
    )
    assert example_path.is_file()
    json.loads(example_path.read_text())

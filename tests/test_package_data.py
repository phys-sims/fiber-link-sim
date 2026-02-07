from __future__ import annotations

import json
from importlib import resources


def test_schema_example_files_are_packaged() -> None:
    examples_dir = resources.files("fiber_link_sim.schema").joinpath("examples")
    example_path = examples_dir.joinpath("qpsk_longhaul_multispan.json")

    assert example_path.is_file()
    payload = json.loads(example_path.read_text())

    assert payload["v"] == "0.1"

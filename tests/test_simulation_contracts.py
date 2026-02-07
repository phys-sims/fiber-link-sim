from __future__ import annotations

import json
from pathlib import Path

from fiber_link_sim.data_models.spec_models import SimulationResult, SimulationSpec
from fiber_link_sim.simulate import simulate


EXAMPLE_DIR = Path("src/fiber_link_sim/schema/examples")


def _load_example(name: str) -> dict:
    return json.loads((EXAMPLE_DIR / name).read_text())


def test_example_specs_validate() -> None:
    for filename in (
        "qpsk_longhaul_manakov.json",
        "ook_smoke.json",
        "pam4_shorthaul.json",
    ):
        spec_data = _load_example(filename)
        spec = SimulationSpec.model_validate(spec_data)
        assert spec.v == "0.1"


def test_simulation_results_validate() -> None:
    for filename in (
        "qpsk_longhaul_manakov.json",
        "ook_smoke.json",
        "pam4_shorthaul.json",
    ):
        spec_data = _load_example(filename)
        result = simulate(spec_data)
        assert result.status == "success"
        SimulationResult.model_validate(result.model_dump())

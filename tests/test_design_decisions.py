from __future__ import annotations

import json
from pathlib import Path

from phys_pipeline import State

from fiber_link_sim.simulate import simulate
from fiber_link_sim.stages.base import SimulationState

EXAMPLE_DIR = Path("src/fiber_link_sim/schema/examples")


def test_fec_disabled_passthrough() -> None:
    spec = json.loads((EXAMPLE_DIR / "ook_smoke.json").read_text())
    spec["processing"]["fec"]["enabled"] = False
    spec["processing"]["fec"]["scheme"] = "none"
    spec["processing"]["fec"]["code_rate"] = 1.0
    result = simulate(spec)
    assert result.summary is not None
    assert result.summary.errors.pre_fec_ber == result.summary.errors.post_fec_ber


def test_state_uses_phys_pipeline_base_type() -> None:
    state = SimulationState()
    assert isinstance(state, State)

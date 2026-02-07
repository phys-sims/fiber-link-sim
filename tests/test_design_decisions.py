from __future__ import annotations

import json
from pathlib import Path

import pytest
from phys_pipeline import State

from fiber_link_sim.adapters.opticommpy import units
from fiber_link_sim.adapters.opticommpy.dsp import resolve_dsp_chain, validate_dsp_chain
from fiber_link_sim.data_models.spec_models import DspBlock, SimulationSpec
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


def test_opticommpy_unit_round_trip() -> None:
    dbm_value = 3.0
    watts = units.dbm_to_watts(dbm_value)
    assert abs(units.watts_to_dbm(watts) - dbm_value) < 1e-9


def test_dsp_default_chain_ordering() -> None:
    coherent_spec = json.loads((EXAMPLE_DIR / "qpsk_longhaul_manakov.json").read_text())
    coherent_spec["processing"]["dsp_chain"] = []
    coherent = SimulationSpec.model_validate(coherent_spec)
    coherent_chain = resolve_dsp_chain(coherent, [])
    assert [block.name for block in coherent_chain] == [
        "resample",
        "matched_filter",
        "cd_comp",
        "mimo_eq",
        "cpr",
        "demap",
    ]

    imdd_spec = json.loads((EXAMPLE_DIR / "ook_smoke.json").read_text())
    imdd_spec["processing"]["dsp_chain"] = []
    imdd = SimulationSpec.model_validate(imdd_spec)
    imdd_chain = resolve_dsp_chain(imdd, [])
    assert [block.name for block in imdd_chain] == [
        "resample",
        "matched_filter",
        "ffe",
        "demap",
    ]


def test_dsp_chain_param_validation() -> None:
    with pytest.raises(ValueError, match="mimo_eq.taps"):
        validate_dsp_chain([DspBlock(name="mimo_eq", params={"taps": 0})])

    with pytest.raises(ValueError, match="resample.out_fs_hz"):
        validate_dsp_chain([DspBlock(name="resample", params={"out_fs_hz": 0})])

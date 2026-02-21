from __future__ import annotations

import json
from pathlib import Path

import pytest
from phys_pipeline import State

from fiber_link_sim.adapters.opticommpy import units
from fiber_link_sim.adapters.opticommpy.dsp import resolve_dsp_chain, validate_dsp_chain
from fiber_link_sim.data_models.spec_models import DspBlock, SimulationSpec
from fiber_link_sim.data_models.stage_models import DspSpecSlice
from fiber_link_sim.simulate import simulate
from fiber_link_sim.stages.base import SimulationState
from fiber_link_sim.utils import preserve_numpy_random_state

EXAMPLE_DIR = Path("src/fiber_link_sim/schema/examples")


@pytest.mark.integration
@pytest.mark.opticommpy
@pytest.mark.slow
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
    coherent_chain = resolve_dsp_chain(DspSpecSlice.from_spec(coherent), [])
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
    imdd_chain = resolve_dsp_chain(DspSpecSlice.from_spec(imdd), [])
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


def test_autotune_enabled_returns_not_implemented() -> None:
    spec = json.loads((EXAMPLE_DIR / "ook_smoke.json").read_text())
    spec["processing"]["autotune"] = {"enabled": True, "budget_trials": 3}
    result = simulate(spec)
    assert result.status == "error"
    assert result.error is not None
    assert result.error.code == "not_implemented"


def test_preserve_numpy_random_state_restores() -> None:
    import numpy as np

    before = np.random.get_state()
    with preserve_numpy_random_state(seed=123):
        _ = np.random.rand(4)
    after = np.random.get_state()
    assert before[0] == after[0]
    assert np.array_equal(before[1], after[1])
    assert before[2:] == after[2:]


def test_latency_metadata_records_v1_frontend_scope_assumption() -> None:
    spec = json.loads((EXAMPLE_DIR / "ook_smoke.json").read_text())
    result = simulate(spec)
    assert result.summary is not None
    assumptions = result.summary.latency_metadata.assumptions
    assert any("out-of-scope for v1 demo" in item for item in assumptions)


def test_latency_model_can_exclude_queueing_from_total() -> None:
    spec = json.loads((EXAMPLE_DIR / "ook_smoke.json").read_text())
    spec["latency_model"]["include_queueing_in_total"] = False
    result = simulate(spec)
    assert result.summary is not None
    assumptions = result.summary.latency_metadata.assumptions
    assert any("include_queueing_in_total=false" in item for item in assumptions)


def test_latency_model_can_exclude_processing_from_total() -> None:
    spec = json.loads((EXAMPLE_DIR / "ook_smoke.json").read_text())
    spec["latency_model"]["include_processing_in_total"] = False
    result = simulate(spec)
    assert result.summary is not None
    assumptions = result.summary.latency_metadata.assumptions
    assert any("include_processing_in_total=false" in item for item in assumptions)

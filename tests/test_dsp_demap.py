from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from optic.comm import modulation  # type: ignore[import-untyped]

from fiber_link_sim.adapters.opticommpy.dsp import run_dsp_chain
from fiber_link_sim.data_models.spec_models import DspBlock, SimulationSpec
from fiber_link_sim.data_models.stage_models import DspSpecSlice

EXAMPLE_DIR = Path("src/fiber_link_sim/schema/examples")


def _load_spec() -> SimulationSpec:
    data = json.loads((EXAMPLE_DIR / "qpsk_longhaul_manakov.json").read_text())
    data["runtime"]["samples_per_symbol"] = 1
    return SimulationSpec.model_validate(data)


@pytest.mark.opticommpy
def test_demap_outputs_hard_bits_and_llrs() -> None:
    spec = _load_spec()
    constellation = modulation.grayMapping(4, "psk")
    samples = np.tile(constellation, 16)
    dsp_out = run_dsp_chain(
        DspSpecSlice.from_spec(spec), samples, [DspBlock(name="demap", params={"soft": True})]
    )
    assert dsp_out.hard_bits is not None
    assert dsp_out.llrs is not None
    assert dsp_out.hard_bits.size == samples.size * 2
    assert dsp_out.llrs.size == dsp_out.hard_bits.size


@pytest.mark.opticommpy
def test_demap_hard_bits_without_llrs() -> None:
    spec = _load_spec()
    constellation = modulation.grayMapping(4, "psk")
    samples = np.tile(constellation, 8)
    dsp_out = run_dsp_chain(
        DspSpecSlice.from_spec(spec), samples, [DspBlock(name="demap", params={"soft": False})]
    )
    assert dsp_out.hard_bits is not None
    assert dsp_out.llrs is None
    assert dsp_out.hard_bits.size == samples.size * 2

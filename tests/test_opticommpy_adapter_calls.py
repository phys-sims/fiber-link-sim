from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from fiber_link_sim.adapters.opticommpy.stages import ADAPTERS
from fiber_link_sim.data_models.spec_models import SimulationSpec
from fiber_link_sim.data_models.stage_models import (
    ChannelSpecSlice,
    DspSpecSlice,
    RxFrontEndSpecSlice,
    TxSpecSlice,
)

EXAMPLE_DIR = Path("src/fiber_link_sim/schema/examples")


def _load_example(name: str) -> dict:
    return json.loads((EXAMPLE_DIR / name).read_text())


def _small_spec(name: str) -> SimulationSpec:
    spec = _load_example(name)
    spec["runtime"]["n_symbols"] = 256
    spec["runtime"]["samples_per_symbol"] = 2
    spec["propagation"]["effects"] = {
        "dispersion": False,
        "nonlinearity": False,
        "ase": False,
        "pmd": False,
        "env_effects": False,
    }
    amplifier = spec["spans"]["amplifier"]
    amplifier["type"] = "none"
    amplifier["mode"] = "none"
    amplifier.pop("max_gain_db", None)
    amplifier.pop("fixed_gain_db", None)
    amplifier.pop("noise_figure_db", None)
    spec["processing"]["dsp_chain"] = []
    if spec["signal"]["format"] == "coherent_qpsk":
        spec["runtime"]["n_symbols"] = max(spec["runtime"]["n_symbols"], 1024)
    return SimulationSpec.model_validate(spec)


@pytest.mark.opticommpy
@pytest.mark.slow
def test_adapter_chain_coherent_qpsk() -> None:
    spec = _small_spec("qpsk_longhaul_1span.json")
    tx_out = ADAPTERS.tx.run(TxSpecSlice.from_spec(spec), seed=123)
    assert tx_out.signal is not None
    assert tx_out.symbols.size > 0

    channel_out = ADAPTERS.channel.run(ChannelSpecSlice.from_spec(spec), tx_out.signal, seed=456)
    assert channel_out.n_spans >= 1
    assert channel_out.osnr_db is None

    rx_out = ADAPTERS.rx_frontend.run(
        RxFrontEndSpecSlice.from_spec(spec), np.asarray(channel_out.signal), seed=789
    )
    assert "lo_power_dbm" in rx_out.params
    assert rx_out.samples.size > 0

    dsp_out = ADAPTERS.dsp.run(
        DspSpecSlice.from_spec(spec), rx_out.samples, spec.processing.dsp_chain
    )
    assert dsp_out.symbols.size > 0
    assert dsp_out.hard_bits is not None

    metrics_out = ADAPTERS.metrics.compute(
        dsp_out.symbols, tx_out.symbols, TxSpecSlice.from_spec(spec)
    )
    assert np.isfinite(metrics_out.pre_fec_ber)
    assert np.isfinite(metrics_out.snr_db)
    assert np.isfinite(metrics_out.evm_rms)


@pytest.mark.opticommpy
@pytest.mark.slow
def test_adapter_chain_imdd_ook() -> None:
    spec = _small_spec("ook_smoke.json")
    tx_out = ADAPTERS.tx.run(TxSpecSlice.from_spec(spec), seed=222)
    assert tx_out.signal is not None
    assert tx_out.symbols.size > 0

    channel_out = ADAPTERS.channel.run(ChannelSpecSlice.from_spec(spec), tx_out.signal, seed=333)
    assert channel_out.n_spans >= 1
    assert channel_out.osnr_db is None

    rx_out = ADAPTERS.rx_frontend.run(
        RxFrontEndSpecSlice.from_spec(spec), np.asarray(channel_out.signal), seed=444
    )
    assert "pd_bandwidth_hz" in rx_out.params
    assert rx_out.samples.size > 0

    dsp_out = ADAPTERS.dsp.run(
        DspSpecSlice.from_spec(spec), rx_out.samples, spec.processing.dsp_chain
    )
    assert dsp_out.symbols.size > 0
    assert dsp_out.hard_bits is not None

    metrics_out = ADAPTERS.metrics.compute(
        dsp_out.symbols, tx_out.symbols, TxSpecSlice.from_spec(spec)
    )
    assert np.isfinite(metrics_out.pre_fec_ber)

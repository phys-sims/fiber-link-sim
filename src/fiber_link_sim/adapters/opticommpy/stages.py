from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from optic.comm import metrics as opti_metrics  # type: ignore[import-untyped]
from optic.models import channels  # type: ignore[import-untyped]
from optic.models import tx as opti_tx

from fiber_link_sim.adapters.opticommpy import units
from fiber_link_sim.adapters.opticommpy.dsp import run_dsp_chain
from fiber_link_sim.adapters.opticommpy.metrics import MetricsOutput, compute_metrics
from fiber_link_sim.adapters.opticommpy.param_builders import build_channel_params, build_tx_params
from fiber_link_sim.adapters.opticommpy.rx import run_rx_frontend
from fiber_link_sim.adapters.opticommpy.types import (
    ChannelOutput,
    DspOutput,
    FecOutput,
    RxOutput,
    TxOutput,
)
from fiber_link_sim.data_models.spec_models import DspBlock, SimulationSpec


@dataclass(slots=True)
class TxAdapter:
    def run(self, spec: SimulationSpec, seed: int) -> TxOutput:
        np.random.seed(seed)
        if spec.signal.format == "coherent_qpsk":
            param = build_tx_params(spec, seed, "coherent")
            signal, symbols, param_out = opti_tx.simpleWDMTx(param)
            return TxOutput(signal=signal, symbols=symbols, params=param_out)

        param = build_tx_params(spec, seed, "pam")
        signal, symbols, param_out = opti_tx.pamTransmitter(param)
        if isinstance(param_out, np.ndarray):
            raise ValueError("unexpected PAM transmitter output signature")
        return TxOutput(signal=signal, symbols=symbols, params=param_out)


@dataclass(slots=True)
class ChannelAdapter:
    def run(self, spec: SimulationSpec, signal: object, seed: int) -> ChannelOutput:
        np.random.seed(seed)
        param, layout = build_channel_params(spec, seed)

        if spec.signal.format == "coherent_qpsk":
            out = channels.manakovSSF(signal, param)
        else:
            out = channels.ssfm(signal, param)

        if isinstance(out, tuple):
            signal_out, params = out
        else:
            signal_out = out
            params = param

        amp_gain_db = getattr(param, "amp_gain_db", None)
        span_loss_db = getattr(param, "span_loss_db", None)
        if amp_gain_db is not None and span_loss_db is not None and param.amp in {"edfa", "ideal"}:
            delta_db = (amp_gain_db - span_loss_db) * layout.n_spans
            if abs(delta_db) > 1e-9:
                signal_out = np.asarray(signal_out) * 10 ** (delta_db / 20)

        osnr_db = None
        if spec.spans.amplifier.type == "edfa" and spec.propagation.effects.ase:
            osnr_lin = opti_metrics.calcLinOSNR(
                layout.n_spans,
                units.dbm_to_watts(spec.transceiver.tx.launch_power_dbm),
                spec.fiber.alpha_db_per_km,
                layout.span_length_km,
                40.0,
                NF=spec.spans.amplifier.noise_figure_db or 0.0,
                Fc=param.Fc,
            )
            osnr_value = float(getattr(osnr_lin, "mean", lambda: osnr_lin)())
            osnr_db = units.linear_to_db(osnr_value)

        return ChannelOutput(
            signal=signal_out,
            params=params,
            osnr_db=osnr_db,
            n_spans=layout.n_spans,
        )


@dataclass(slots=True)
class RxFrontEndAdapter:
    def run(self, spec: SimulationSpec, signal: np.ndarray, seed: int) -> RxOutput:
        np.random.seed(seed)
        return run_rx_frontend(spec, signal, seed)


@dataclass(slots=True)
class DSPAdapter:
    def run(self, spec: SimulationSpec, samples: np.ndarray, blocks: list[DspBlock]) -> DspOutput:
        return run_dsp_chain(spec, samples, blocks)


@dataclass(slots=True)
class FECAdapter:
    def run(self, spec: SimulationSpec, pre_fec_ber: float) -> FecOutput:
        if spec.processing.fec.enabled:
            code_rate = spec.processing.fec.code_rate
            post_fec_ber = max(pre_fec_ber * (1.0 - code_rate) * 0.2, 1e-12)
        else:
            post_fec_ber = pre_fec_ber
        fer = min(1.0, post_fec_ber * 10.0)
        return FecOutput(post_fec_ber=post_fec_ber, fer=fer)


@dataclass(slots=True)
class MetricsAdapter:
    def compute(
        self, symb_rx: np.ndarray, symb_tx: np.ndarray, spec: SimulationSpec
    ) -> MetricsOutput:
        return compute_metrics(symb_rx, symb_tx, spec.signal)


@dataclass(slots=True)
class OptiCommPyAdapters:
    tx: TxAdapter = field(default_factory=TxAdapter)
    channel: ChannelAdapter = field(default_factory=ChannelAdapter)
    rx_frontend: RxFrontEndAdapter = field(default_factory=RxFrontEndAdapter)
    dsp: DSPAdapter = field(default_factory=DSPAdapter)
    fec: FECAdapter = field(default_factory=FECAdapter)
    metrics: MetricsAdapter = field(default_factory=MetricsAdapter)


ADAPTERS = OptiCommPyAdapters()

__all__ = ["ADAPTERS", "OptiCommPyAdapters"]

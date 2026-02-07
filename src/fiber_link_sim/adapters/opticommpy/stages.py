from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from optic.comm import metrics as opti_metrics  # type: ignore[import-untyped]
from optic.models import channels, devices, tx as opti_tx  # type: ignore[import-untyped]

from fiber_link_sim.adapters.opticommpy import units
from fiber_link_sim.adapters.opticommpy.dsp import run_dsp_chain
from fiber_link_sim.adapters.opticommpy.metrics import MetricsOutput, compute_metrics
from fiber_link_sim.adapters.opticommpy.param_builders import (
    build_channel_params,
    build_lo_params,
    build_pd_params,
    build_tx_params,
)
from fiber_link_sim.adapters.opticommpy.types import ChannelOutput, DspOutput, FecOutput, RxOutput, TxOutput
from fiber_link_sim.data_models.spec_models import DspBlock, SimulationSpec


@dataclass(slots=True)
class TxAdapter:
    def run(self, spec: SimulationSpec, seed: int) -> TxOutput:
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

        osnr_db = None
        if spec.spans.amplifier.type == "edfa":
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
        if spec.transceiver.rx.coherent:
            lo_param = build_lo_params(spec, seed, signal.shape[0])
            lo = devices.basicLaserModel(lo_param)
            pd_param = build_pd_params(spec, seed)
            samples = devices.pdmCoherentReceiver(signal, lo, param=pd_param)
            return RxOutput(samples=samples, params={"lo_power_dbm": lo_param.P})

        pd_param = build_pd_params(spec, seed)
        current = devices.photodiode(signal, pd_param)
        return RxOutput(samples=current, params={"pd_bandwidth_hz": pd_param.B})


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
    def compute(self, symb_rx: np.ndarray, symb_tx: np.ndarray, spec: SimulationSpec) -> MetricsOutput:
        return compute_metrics(symb_rx, symb_tx, spec.signal)


@dataclass(slots=True)
class OptiCommPyAdapters:
    tx: TxAdapter = TxAdapter()
    channel: ChannelAdapter = ChannelAdapter()
    rx_frontend: RxFrontEndAdapter = RxFrontEndAdapter()
    dsp: DSPAdapter = DSPAdapter()
    fec: FECAdapter = FECAdapter()
    metrics: MetricsAdapter = MetricsAdapter()


ADAPTERS = OptiCommPyAdapters()

__all__ = ["ADAPTERS", "OptiCommPyAdapters"]

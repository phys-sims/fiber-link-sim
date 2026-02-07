from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from optic.comm import fec as opti_fec  # type: ignore[import-untyped]
from optic.comm import metrics as opti_metrics
from optic.comm import modulation
from optic.models import channels  # type: ignore[import-untyped]
from optic.models import tx as opti_tx
from optic.utils import parameters  # type: ignore[import-untyped]

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
    def run(
        self,
        spec: SimulationSpec,
        tx_symbols: np.ndarray,
        llrs: np.ndarray | None,
        hard_bits: np.ndarray | None,
        pre_fec_ber: float,
    ) -> FecOutput:
        if not spec.processing.fec.enabled:
            post_fec_ber = pre_fec_ber
            fer = min(1.0, post_fec_ber * 10.0)
            return FecOutput(post_fec_ber=post_fec_ber, fer=fer)
        if spec.processing.fec.scheme != "ldpc":
            raise ValueError(f"unsupported FEC scheme: {spec.processing.fec.scheme}")
        if llrs is None and hard_bits is None:
            raise ValueError("FEC enabled but DSP demap produced no LLRs or hard bits")

        ldpc_params = _build_ldpc_params(spec.processing.fec.params)
        llr_vector = _prepare_llrs(llrs, hard_bits)
        tx_bits = _tx_bits_from_symbols(tx_symbols, spec)
        n_bits = min(llr_vector.shape[0], tx_bits.shape[0])
        n_codeword = ldpc_params.H.shape[1]
        n_codewords = n_bits // n_codeword
        if n_codewords < 1:
            raise ValueError("insufficient bits to form an LDPC codeword")

        trim_len = n_codewords * n_codeword
        llr_vector = llr_vector[:trim_len]
        tx_bits = tx_bits[:trim_len]
        llr_matrix = llr_vector.reshape(n_codewords, n_codeword).T
        decoded_bits, _ = opti_fec.decodeLDPC(llr_matrix, ldpc_params)
        decoded_bits = np.asarray(decoded_bits).astype(int)
        decoded_vector = decoded_bits.T.reshape(-1)

        bit_errors = decoded_vector != tx_bits
        post_fec_ber = float(np.mean(bit_errors))
        fer = float(np.mean(bit_errors.reshape(n_codewords, n_codeword).any(axis=1)))
        return FecOutput(post_fec_ber=post_fec_ber, fer=fer)


def _build_ldpc_params(params: dict[str, object]) -> parameters:
    if "H" not in params:
        raise ValueError("processing.fec.params.H is required for LDPC decoding")
    matrix = np.asarray(params["H"])
    if matrix.ndim != 2:
        raise ValueError("processing.fec.params.H must be a 2D parity-check matrix")
    ldpc_params = parameters()
    ldpc_params.H = matrix.astype(int)
    raw_max_iter = params.get("max_iter", params.get("max_iters", 25))
    if isinstance(raw_max_iter, (int, float, np.integer, np.floating, str)):
        ldpc_params.maxIter = int(raw_max_iter)
    else:
        ldpc_params.maxIter = 25
    ldpc_params.alg = str(params.get("alg", "SPA"))
    prec = params.get("prec", np.float32)
    if isinstance(prec, str):
        prec = getattr(np, prec)
    ldpc_params.prec = prec
    return ldpc_params


def _prepare_llrs(
    llrs: np.ndarray | None, hard_bits: np.ndarray | None, magnitude: float = 5.0
) -> np.ndarray:
    if llrs is not None:
        return np.asarray(llrs).reshape(-1).astype(np.float32)
    if hard_bits is None:
        raise ValueError("missing LLRs and hard bits for FEC decoding")
    hard_bits = np.asarray(hard_bits).reshape(-1).astype(int)
    return np.where(hard_bits == 0, magnitude, -magnitude).astype(np.float32)


def _tx_bits_from_symbols(tx_symbols: np.ndarray, spec: SimulationSpec) -> np.ndarray:
    order, const_type = _constellation_params(spec.signal.format)
    symbols = np.asarray(tx_symbols).reshape(-1)
    return modulation.demodulateGray(symbols, order, const_type).astype(int)


def _constellation_params(signal_format: str) -> tuple[int, str]:
    if signal_format == "coherent_qpsk":
        return 4, "psk"
    if signal_format == "imdd_ook":
        return 2, "ook"
    return 4, "pam"


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

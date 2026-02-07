from __future__ import annotations

from dataclasses import dataclass
from math import log10

from fiber_link_sim.data_models.spec_models import SimulationSpec
from fiber_link_sim.metrics import (
    ber_from_snr_linear,
    evm_from_snr_linear,
    snr_from_osnr_db,
)
from fiber_link_sim.stages.base import Stage, StageResult, State
from fiber_link_sim.utils import bits_per_symbol, total_link_length_m


@dataclass(slots=True)
class TxStage(Stage):
    spec: SimulationSpec
    name: str = "tx"

    def run(self, state: State) -> StageResult:
        signal = self.spec.signal
        total_bits = (
            signal.frame.payload_bits + signal.frame.preamble_bits + signal.frame.pilot_bits
        )
        state.tx.update(
            {
                "format": signal.format,
                "n_pol": signal.n_pol,
                "symbol_rate_baud": signal.symbol_rate_baud,
                "rolloff": signal.rolloff,
                "total_bits": total_bits,
            }
        )
        state.stats["bits_per_symbol"] = bits_per_symbol(signal)
        state.stats["n_symbols"] = self.spec.runtime.n_symbols
        return StageResult(state=state)


@dataclass(slots=True)
class ChannelStage(Stage):
    spec: SimulationSpec
    name: str = "channel"

    def run(self, state: State) -> StageResult:
        fiber = self.spec.fiber
        spans = self.spec.spans
        total_length_m = total_link_length_m(self.spec.path)
        total_length_km = total_length_m / 1000.0
        if spans.mode == "from_path_segments":
            n_spans = len(self.spec.path.segments)
            span_length_km = total_length_km / max(n_spans, 1)
        else:
            span_length_km = spans.span_length_m / 1000.0
            n_spans = max(1, int(round(total_length_km / span_length_km)))

        span_loss_db = fiber.alpha_db_per_km * span_length_km
        total_loss_db = fiber.alpha_db_per_km * total_length_km
        gain_db = 0.0
        if spans.amplifier.type == "edfa":
            if spans.amplifier.mode == "auto_gain":
                max_gain = spans.amplifier.max_gain_db or span_loss_db
                gain_db = min(span_loss_db, max_gain) * n_spans
            elif spans.amplifier.mode == "fixed_gain":
                gain_db = (spans.amplifier.fixed_gain_db or 0.0) * n_spans

        noise_figure_db = spans.amplifier.noise_figure_db or 0.0
        osnr_db = 20.0 + self.spec.transceiver.tx.launch_power_dbm - total_loss_db + gain_db
        osnr_db -= noise_figure_db

        state.optical.update(
            {
                "total_length_m": total_length_m,
                "n_spans": n_spans,
                "span_loss_db": span_loss_db,
                "gain_db": gain_db,
                "osnr_db": osnr_db,
            }
        )
        return StageResult(state=state)


@dataclass(slots=True)
class RxFrontEndStage(Stage):
    spec: SimulationSpec
    name: str = "rx_frontend"

    def run(self, state: State) -> StageResult:
        osnr_db = float(state.optical.get("osnr_db", 0.0))
        snr_db = snr_from_osnr_db(osnr_db, coherent=self.spec.transceiver.rx.coherent)
        state.rx["snr_db"] = snr_db
        return StageResult(state=state)


@dataclass(slots=True)
class DSPStage(Stage):
    spec: SimulationSpec
    name: str = "dsp"

    def run(self, state: State) -> StageResult:
        snr_db = float(state.rx.get("snr_db", 0.0))
        snr_linear = 10 ** (snr_db / 10.0)
        evm_rms = evm_from_snr_linear(snr_linear)
        state.stats["evm_rms"] = evm_rms
        return StageResult(state=state)


@dataclass(slots=True)
class FECStage(Stage):
    spec: SimulationSpec
    name: str = "fec"

    def run(self, state: State) -> StageResult:
        snr_db = float(state.rx.get("snr_db", 0.0))
        snr_linear = 10 ** (snr_db / 10.0)
        pre_fec_ber = ber_from_snr_linear(self.spec.signal.format, snr_linear)
        if self.spec.processing.fec.enabled:
            code_rate = self.spec.processing.fec.code_rate
            post_fec_ber = max(pre_fec_ber * (1.0 - code_rate) * 0.2, 1e-12)
        else:
            post_fec_ber = pre_fec_ber
        fer = min(1.0, post_fec_ber * 10.0)
        state.stats.update(
            {
                "pre_fec_ber": pre_fec_ber,
                "post_fec_ber": post_fec_ber,
                "fer": fer,
            }
        )
        return StageResult(state=state)


@dataclass(slots=True)
class MetricsStage(Stage):
    spec: SimulationSpec
    name: str = "metrics"

    def run(self, state: State) -> StageResult:
        signal = self.spec.signal
        total_length_m = float(state.optical.get("total_length_m", 0.0))
        bits_per_symbol_val = int(state.stats.get("bits_per_symbol", 1))
        total_bits = int(state.tx.get("total_bits", 0))

        c_m_s = 299_792_458.0
        propagation_s = total_length_m / (c_m_s / self.spec.fiber.n_group)
        serialization_s = total_bits / (signal.symbol_rate_baud * bits_per_symbol_val)
        processing_est_s = max(1e-6, self.spec.runtime.n_symbols / signal.symbol_rate_baud * 0.1)
        total_latency_s = propagation_s + serialization_s + processing_est_s

        raw_line_rate = signal.symbol_rate_baud * bits_per_symbol_val
        if self.spec.processing.fec.enabled:
            net_after_fec = raw_line_rate * self.spec.processing.fec.code_rate
        else:
            net_after_fec = raw_line_rate
        goodput = net_after_fec * (signal.frame.payload_bits / max(total_bits, 1))

        osnr_db = float(state.optical.get("osnr_db", 0.0))
        summary = {
            "latency_s": {
                "propagation": propagation_s,
                "serialization": serialization_s,
                "processing_est": processing_est_s,
                "total": total_latency_s,
            },
            "throughput_bps": {
                "raw_line_rate": raw_line_rate,
                "net_after_fec": net_after_fec,
                "goodput_est": goodput,
            },
            "errors": {
                "pre_fec_ber": float(state.stats.get("pre_fec_ber", 0.0)),
                "post_fec_ber": float(state.stats.get("post_fec_ber", 0.0)),
                "fer": float(state.stats.get("fer", 0.0)),
            },
            "osnr_db": osnr_db,
            "snr_db": float(state.rx.get("snr_db", 0.0)),
            "evm_rms": float(state.stats.get("evm_rms", 0.0)),
            "q_factor_db": 20.0 * log10(1.0 / max(state.stats.get("evm_rms", 1.0), 1e-6)),
        }
        warnings: list[str] = []
        if osnr_db < 10.0:
            warnings.append("OSNR is low; results may be unreliable.")
        return StageResult(state=state, metrics=summary, warnings=warnings)

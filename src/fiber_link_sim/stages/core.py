from __future__ import annotations

import time
from dataclasses import dataclass
from math import log10

import numpy as np

from fiber_link_sim.adapters.opticommpy import ADAPTERS
from fiber_link_sim.artifacts import (
    ArtifactPayload,
    build_eye_traces,
    compute_phase_error,
    compute_psd,
)
from fiber_link_sim.stages.base import SimulationState, Stage, StageResult
from fiber_link_sim.stages.configs import (
    ArtifactsStageConfig,
    ChannelStageConfig,
    DSPStageConfig,
    FECStageConfig,
    MetricsStageConfig,
    RxFrontEndStageConfig,
    TxStageConfig,
)
from fiber_link_sim.utils import bits_per_symbol, total_link_length_m


@dataclass(slots=True)
class TxStage(Stage):
    cfg: TxStageConfig
    name: str = "tx"

    def process(self, state: SimulationState, *, policy: object | None = None) -> StageResult:
        start = time.perf_counter()
        spec = self.cfg.spec
        rng = state.stage_rng(self.name)
        tx_out = ADAPTERS.tx.run(spec, int(rng.integers(0, 2**31 - 1)))

        total_bits = int(spec.runtime.n_symbols * bits_per_symbol(spec.signal))
        if tx_out.signal is None:
            raise ValueError("missing tx waveform")
        if tx_out.symbols is None:
            raise ValueError("missing tx symbols")
        state.store_signal("tx", "symbols", tx_out.symbols, units="symbols")
        state.store_signal("tx", "waveform", tx_out.signal, units="arb")
        state.stats["bits_per_symbol"] = bits_per_symbol(spec.signal)
        state.stats["n_symbols"] = spec.runtime.n_symbols
        state.stats["total_bits"] = total_bits
        state.meta.setdefault("stage_timings", {})[self.name] = time.perf_counter() - start
        return StageResult(state=state)


@dataclass(slots=True)
class ChannelStage(Stage):
    cfg: ChannelStageConfig
    name: str = "channel"

    def process(self, state: SimulationState, *, policy: object | None = None) -> StageResult:
        start = time.perf_counter()
        spec = self.cfg.spec
        rng = state.stage_rng(self.name)
        signal = state.load_signal("tx", "waveform")
        if signal is None:
            raise ValueError("missing tx waveform for channel stage")
        channel_out = ADAPTERS.channel.run(spec, signal, int(rng.integers(0, 2**31 - 1)))

        total_length_m = total_link_length_m(spec.path)
        state.store_signal("optical", "waveform", channel_out.signal, units="arb")
        state.stats.update(
            {
                "total_length_m": total_length_m,
                "n_spans": channel_out.n_spans,
                "osnr_db": channel_out.osnr_db,
            }
        )
        state.meta.setdefault("stage_timings", {})[self.name] = time.perf_counter() - start
        return StageResult(state=state)


@dataclass(slots=True)
class RxFrontEndStage(Stage):
    cfg: RxFrontEndStageConfig
    name: str = "rx_frontend"

    def process(self, state: SimulationState, *, policy: object | None = None) -> StageResult:
        start = time.perf_counter()
        spec = self.cfg.spec
        rng = state.stage_rng(self.name)
        signal = state.load_signal("optical", "waveform")
        if signal is None:
            raise ValueError("missing optical waveform for rx frontend")
        rx_out = ADAPTERS.rx_frontend.run(spec, signal, int(rng.integers(0, 2**31 - 1)))
        state.store_signal("rx", "samples", rx_out.samples, units="arb")
        state.rx["frontend"] = rx_out.params
        state.meta.setdefault("stage_timings", {})[self.name] = time.perf_counter() - start
        return StageResult(state=state)


@dataclass(slots=True)
class DSPStage(Stage):
    cfg: DSPStageConfig
    name: str = "dsp"

    def process(self, state: SimulationState, *, policy: object | None = None) -> StageResult:
        start = time.perf_counter()
        spec = self.cfg.spec
        samples = state.load_signal("rx", "samples")
        if samples is None:
            raise ValueError("missing rx samples for DSP stage")
        dsp_out = ADAPTERS.dsp.run(spec, samples, spec.processing.dsp_chain)
        state.store_signal("rx", "dsp_samples", dsp_out.samples, units="arb")
        state.store_signal("rx", "symbols", dsp_out.symbols, units="symbols")
        if dsp_out.hard_bits is not None:
            ref = state.store_blob(
                "hard_bits", dsp_out.hard_bits, role="rx:hard_bits", units="bits"
            )
            state.rx["hard_bits_ref"] = ref
        if dsp_out.llrs is not None:
            ref = state.store_blob("llrs", dsp_out.llrs, role="rx:llrs", units="llr")
            state.rx["llrs_ref"] = ref
        state.stats["dsp"] = dsp_out.params
        state.meta.setdefault("stage_timings", {})[self.name] = time.perf_counter() - start
        return StageResult(state=state)


@dataclass(slots=True)
class FECStage(Stage):
    cfg: FECStageConfig
    name: str = "fec"

    def process(self, state: SimulationState, *, policy: object | None = None) -> StageResult:
        start = time.perf_counter()
        spec = self.cfg.spec
        if "pre_fec_ber" not in state.stats:
            symb_rx = state.load_signal("rx", "symbols")
            symb_tx = state.load_signal("tx", "symbols")
            if symb_rx is None or symb_tx is None:
                raise ValueError("missing symbols for FEC stage")
            metrics = ADAPTERS.metrics.compute(symb_rx, symb_tx, spec)
            state.stats.update(
                {
                    "pre_fec_ber": metrics.pre_fec_ber,
                    "snr_db": metrics.snr_db,
                    "evm_rms": metrics.evm_rms,
                }
            )
        pre_fec_ber = float(state.stats.get("pre_fec_ber", 0.0))
        llrs_ref = state.rx.get("llrs_ref")
        hard_bits_ref = state.rx.get("hard_bits_ref")
        llrs = state.load_ref(llrs_ref) if llrs_ref else None
        hard_bits = state.load_ref(hard_bits_ref) if hard_bits_ref else None
        tx_symbols = state.load_signal("tx", "symbols")
        if tx_symbols is None:
            raise ValueError("missing tx symbols for FEC stage")
        try:
            fec_out = ADAPTERS.fec.run(spec, tx_symbols, llrs, hard_bits, pre_fec_ber)
            post_fec_ber = fec_out.post_fec_ber
            fer = fec_out.fer
        except Exception as exc:
            state.meta.setdefault("warnings", []).append(
                f"FEC decode failed; using pre-FEC metrics ({exc})."
            )
            post_fec_ber = pre_fec_ber
            fer = min(1.0, pre_fec_ber * 10.0)
        state.stats.update(
            {
                "post_fec_ber": post_fec_ber,
                "fer": fer,
            }
        )
        state.meta.setdefault("stage_timings", {})[self.name] = time.perf_counter() - start
        return StageResult(state=state)


@dataclass(slots=True)
class MetricsStage(Stage):
    cfg: MetricsStageConfig
    name: str = "metrics"

    def process(self, state: SimulationState, *, policy: object | None = None) -> StageResult:
        start = time.perf_counter()
        spec = self.cfg.spec
        if "pre_fec_ber" not in state.stats:
            symb_rx = state.load_signal("rx", "symbols")
            symb_tx = state.load_signal("tx", "symbols")
            if symb_rx is None or symb_tx is None:
                raise ValueError("missing symbols for metrics stage")
            metrics = ADAPTERS.metrics.compute(symb_rx, symb_tx, spec)
            state.stats.update(
                {
                    "pre_fec_ber": metrics.pre_fec_ber,
                    "snr_db": metrics.snr_db,
                    "evm_rms": metrics.evm_rms,
                }
            )

        total_length_m = float(state.stats.get("total_length_m", 0.0))
        bits_per_symbol_val = int(state.stats.get("bits_per_symbol", 1))
        total_bits = int(state.stats.get("total_bits", 0))
        latency_model = spec.latency_model

        c_m_s = 299_792_458.0
        propagation_s = total_length_m / (c_m_s / spec.fiber.n_group)
        serialization_s = (
            total_bits
            / (spec.signal.symbol_rate_baud * bits_per_symbol_val)
            * latency_model.serialization_weight
        )
        processing_est_s = max(
            latency_model.processing_floor_s,
            spec.runtime.n_symbols / spec.signal.symbol_rate_baud * latency_model.processing_weight,
        )
        total_latency_s = propagation_s + serialization_s + processing_est_s

        raw_line_rate = spec.signal.symbol_rate_baud * bits_per_symbol_val
        if spec.processing.fec.enabled:
            net_after_fec = raw_line_rate * spec.processing.fec.code_rate
        else:
            net_after_fec = raw_line_rate
        goodput = net_after_fec * (spec.signal.frame.payload_bits / max(total_bits, 1))

        osnr_db = state.stats.get("osnr_db")
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
            "snr_db": float(state.stats.get("snr_db", 0.0)),
            "evm_rms": float(state.stats.get("evm_rms", 0.0)),
            "q_factor_db": 20.0 * log10(1.0 / max(state.stats.get("evm_rms", 1.0), 1e-6)),
        }
        state.stats["summary"] = summary

        warnings: list[str] = []
        if osnr_db is not None and osnr_db < 10.0:
            warnings.append("OSNR is low; results may be unreliable.")
        state.meta.setdefault("warnings", []).extend(warnings)
        state.meta.setdefault("stage_timings", {})[self.name] = time.perf_counter() - start
        return StageResult(state=state)


@dataclass(slots=True)
class ArtifactsStage(Stage):
    cfg: ArtifactsStageConfig
    name: str = "artifacts"

    def process(self, state: SimulationState, *, policy: object | None = None) -> StageResult:
        start = time.perf_counter()
        spec = self.cfg.spec
        if spec.outputs.artifact_level == "none":
            return StageResult(state=state)

        if not spec.outputs.return_waveforms:
            return StageResult(state=state)

        waveforms: list[tuple[str, np.ndarray | None]] = [
            ("tx_waveform", state.load_signal("tx", "waveform")),
            ("optical_waveform", state.load_signal("optical", "waveform")),
            ("rx_samples", state.load_signal("rx", "samples")),
        ]

        for name, waveform in waveforms:
            if waveform is None:
                continue
            state.artifacts.append(
                state.artifact_store.save_npz_artifact(
                    ArtifactPayload(name=name, arrays={"data": np.asarray(waveform)})
                )
            )

        fs_hz = spec.signal.symbol_rate_baud * spec.runtime.samples_per_symbol
        tx_waveform = state.load_signal("tx", "waveform")
        if tx_waveform is not None:
            freqs, psd_db = compute_psd(np.asarray(tx_waveform), fs_hz)
            if freqs.size:
                state.artifacts.append(
                    state.artifact_store.save_npz_artifact(
                        ArtifactPayload(name="tx_psd", arrays={"freq_hz": freqs, "psd_db": psd_db})
                    )
                )

        optical_waveform = state.load_signal("optical", "waveform")
        if optical_waveform is not None:
            freqs, psd_db = compute_psd(np.asarray(optical_waveform), fs_hz)
            if freqs.size:
                state.artifacts.append(
                    state.artifact_store.save_npz_artifact(
                        ArtifactPayload(
                            name="channel_psd", arrays={"freq_hz": freqs, "psd_db": psd_db}
                        )
                    )
                )

        rx_samples = state.load_signal("rx", "samples")
        if rx_samples is not None:
            traces = build_eye_traces(np.asarray(rx_samples), spec.runtime.samples_per_symbol)
            if traces.size:
                state.artifacts.append(
                    state.artifact_store.save_npz_artifact(
                        ArtifactPayload(name="rx_eye", arrays={"traces": traces})
                    )
                )

        dsp_samples = state.load_signal("rx", "dsp_samples")
        if dsp_samples is not None:
            traces = build_eye_traces(np.asarray(dsp_samples), spec.runtime.samples_per_symbol)
            if traces.size:
                state.artifacts.append(
                    state.artifact_store.save_npz_artifact(
                        ArtifactPayload(name="dsp_eye", arrays={"traces": traces})
                    )
                )

        rx_symbols = state.load_signal("rx", "symbols")
        if rx_symbols is not None:
            symbols = np.asarray(rx_symbols).reshape(-1)
            if symbols.size:
                state.artifacts.append(
                    state.artifact_store.save_npz_artifact(
                        ArtifactPayload(name="dsp_constellation", arrays={"symbols": symbols})
                    )
                )

            tx_symbols = state.load_signal("tx", "symbols")
            phase_error = compute_phase_error(symbols, tx_symbols)
            if phase_error.size:
                state.artifacts.append(
                    state.artifact_store.save_npz_artifact(
                        ArtifactPayload(name="dsp_phase_error", arrays={"radians": phase_error})
                    )
                )

        state.meta.setdefault("stage_timings", {})[self.name] = time.perf_counter() - start
        return StageResult(state=state)


__all__ = [
    "TxStage",
    "ChannelStage",
    "RxFrontEndStage",
    "DSPStage",
    "FECStage",
    "MetricsStage",
    "ArtifactsStage",
]

from __future__ import annotations

from dataclasses import dataclass
from math import log10
from pathlib import Path

import numpy as np

from fiber_link_sim.adapters.opticommpy import ADAPTERS
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
        spec = self.cfg.spec
        rng = state.stage_rng(self.name)
        tx_out = ADAPTERS.tx.run(spec, int(rng.integers(0, 2**31 - 1)))

        total_bits = int(spec.runtime.n_symbols * bits_per_symbol(spec.signal))
        state.tx.update(
            {
                "format": spec.signal.format,
                "n_pol": spec.signal.n_pol,
                "symbol_rate_baud": spec.signal.symbol_rate_baud,
                "rolloff": spec.signal.rolloff,
                "total_bits": total_bits,
                "symbols": tx_out.symbols,
                "waveform": tx_out.signal,
            }
        )
        state.stats["bits_per_symbol"] = bits_per_symbol(spec.signal)
        state.stats["n_symbols"] = spec.runtime.n_symbols
        return StageResult(state=state)


@dataclass(slots=True)
class ChannelStage(Stage):
    cfg: ChannelStageConfig
    name: str = "channel"

    def process(self, state: SimulationState, *, policy: object | None = None) -> StageResult:
        spec = self.cfg.spec
        rng = state.stage_rng(self.name)
        signal = state.tx.get("waveform")
        if signal is None:
            raise ValueError("missing tx waveform for channel stage")
        channel_out = ADAPTERS.channel.run(spec, signal, int(rng.integers(0, 2**31 - 1)))

        total_length_m = total_link_length_m(spec.path)
        state.optical.update(
            {
                "total_length_m": total_length_m,
                "n_spans": channel_out.n_spans,
                "osnr_db": channel_out.osnr_db,
                "waveform": channel_out.signal,
            }
        )
        return StageResult(state=state)


@dataclass(slots=True)
class RxFrontEndStage(Stage):
    cfg: RxFrontEndStageConfig
    name: str = "rx_frontend"

    def process(self, state: SimulationState, *, policy: object | None = None) -> StageResult:
        spec = self.cfg.spec
        rng = state.stage_rng(self.name)
        signal = state.optical.get("waveform")
        if signal is None:
            raise ValueError("missing optical waveform for rx frontend")
        rx_out = ADAPTERS.rx_frontend.run(spec, signal, int(rng.integers(0, 2**31 - 1)))
        state.rx.update({"samples": rx_out.samples, "frontend": rx_out.params})
        return StageResult(state=state)


@dataclass(slots=True)
class DSPStage(Stage):
    cfg: DSPStageConfig
    name: str = "dsp"

    def process(self, state: SimulationState, *, policy: object | None = None) -> StageResult:
        spec = self.cfg.spec
        samples = state.rx.get("samples")
        if samples is None:
            raise ValueError("missing rx samples for DSP stage")
        rng = state.stage_rng(self.name)
        np.random.seed(int(rng.integers(0, 2**31 - 1)))
        dsp_out = ADAPTERS.dsp.run(spec, samples, spec.processing.dsp_chain)
        state.rx["symbols"] = dsp_out.symbols
        state.stats["dsp"] = dsp_out.params
        return StageResult(state=state)


@dataclass(slots=True)
class FECStage(Stage):
    cfg: FECStageConfig
    name: str = "fec"

    def process(self, state: SimulationState, *, policy: object | None = None) -> StageResult:
        spec = self.cfg.spec
        if "pre_fec_ber" not in state.stats:
            symb_rx = state.rx.get("symbols")
            symb_tx = state.tx.get("symbols")
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
        fec_out = ADAPTERS.fec.run(spec, pre_fec_ber)
        state.stats.update(
            {
                "post_fec_ber": fec_out.post_fec_ber,
                "fer": fec_out.fer,
            }
        )
        if spec.processing.fec.enabled:
            state.meta.setdefault("warnings", []).append(
                "LDPC decoding is approximated until parity-check matrices are provided."
            )
        return StageResult(state=state)


@dataclass(slots=True)
class MetricsStage(Stage):
    cfg: MetricsStageConfig
    name: str = "metrics"

    def process(self, state: SimulationState, *, policy: object | None = None) -> StageResult:
        spec = self.cfg.spec
        if "pre_fec_ber" not in state.stats:
            symb_rx = state.rx.get("symbols")
            symb_tx = state.tx.get("symbols")
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

        total_length_m = float(state.optical.get("total_length_m", 0.0))
        bits_per_symbol_val = int(state.stats.get("bits_per_symbol", 1))
        total_bits = int(state.tx.get("total_bits", 0))

        c_m_s = 299_792_458.0
        propagation_s = total_length_m / (c_m_s / spec.fiber.n_group)
        serialization_s = total_bits / (spec.signal.symbol_rate_baud * bits_per_symbol_val)
        processing_est_s = max(1e-6, spec.runtime.n_symbols / spec.signal.symbol_rate_baud * 0.1)
        total_latency_s = propagation_s + serialization_s + processing_est_s

        raw_line_rate = spec.signal.symbol_rate_baud * bits_per_symbol_val
        if spec.processing.fec.enabled:
            net_after_fec = raw_line_rate * spec.processing.fec.code_rate
        else:
            net_after_fec = raw_line_rate
        goodput = net_after_fec * (spec.signal.frame.payload_bits / max(total_bits, 1))

        osnr_db = state.optical.get("osnr_db")
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
        return StageResult(state=state)


@dataclass(slots=True)
class ArtifactsStage(Stage):
    cfg: ArtifactsStageConfig
    name: str = "artifacts"

    def process(self, state: SimulationState, *, policy: object | None = None) -> StageResult:
        spec = self.cfg.spec
        if spec.outputs.artifact_level == "none":
            return StageResult(state=state)

        if not spec.outputs.return_waveforms:
            return StageResult(state=state)

        artifact_root = Path("artifacts") / str(state.meta.get("spec_hash", "unknown"))
        artifact_root.mkdir(parents=True, exist_ok=True)

        waveforms: list[tuple[str, np.ndarray | None]] = [
            ("tx_waveform", state.tx.get("waveform")),
            ("optical_waveform", state.optical.get("waveform")),
            ("rx_samples", state.rx.get("samples")),
        ]

        for name, waveform in waveforms:
            if waveform is None:
                continue
            payload = np.asarray(waveform)
            filename = f"{name}.npz"
            path = artifact_root / filename
            np.savez_compressed(path, data=payload)
            ref = f"artifact://{artifact_root.name}/{filename}"
            state.artifacts.append(
                {
                    "name": name,
                    "type": "npz",
                    "ref": ref,
                    "mime": "application/octet-stream",
                    "bytes": path.stat().st_size,
                }
            )

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

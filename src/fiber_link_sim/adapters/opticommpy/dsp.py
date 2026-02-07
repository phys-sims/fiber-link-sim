from __future__ import annotations

import math
from typing import Any

import numpy as np
from optic.comm import metrics as opti_metrics  # type: ignore[import-untyped]
from optic.comm import modulation
from optic.dsp import carrierRecovery, equalization  # type: ignore[import-untyped]
from optic.dsp import core as dsp_core
from optic.utils import dec2bitarray  # type: ignore[import-untyped]

from fiber_link_sim.adapters.opticommpy.param_builders import (
    build_edc_params,
    build_mimo_eq_params,
    build_resample_params,
)
from fiber_link_sim.adapters.opticommpy.types import DspOutput
from fiber_link_sim.data_models.spec_models import DspBlock, DSPBlockName, SimulationSpec

_DSP_BLOCKS = {
    "resample",
    "matched_filter",
    "cd_comp",
    "mimo_eq",
    "ffe",
    "cpr",
    "demap",
}

_DEFAULT_COHERENT_CHAIN: tuple[DSPBlockName, ...] = (
    "resample",
    "matched_filter",
    "cd_comp",
    "mimo_eq",
    "cpr",
    "demap",
)
_DEFAULT_IMDD_CHAIN: tuple[DSPBlockName, ...] = ("resample", "matched_filter", "ffe", "demap")


def resolve_dsp_chain(spec: SimulationSpec, blocks: list[DspBlock]) -> list[DspBlock]:
    if blocks:
        chain = list(blocks)
    else:
        if spec.signal.format == "coherent_qpsk":
            chain = [DspBlock(name=name) for name in _DEFAULT_COHERENT_CHAIN]
        else:
            chain = [DspBlock(name=name) for name in _DEFAULT_IMDD_CHAIN]
    validate_dsp_chain(chain)
    return chain


def validate_dsp_chain(blocks: list[DspBlock]) -> None:
    for block in blocks:
        if not block.enabled:
            continue
        name = block.name
        params = block.params
        if name not in _DSP_BLOCKS:
            continue
        if name == "resample" and "out_fs_hz" in params:
            out_fs = float(params["out_fs_hz"])
            if out_fs <= 0:
                raise ValueError("resample.out_fs_hz must be > 0")
        if name in {"mimo_eq", "ffe"}:
            taps = int(params.get("taps", 1))
            mu = float(params.get("mu", 1e-3))
            if taps < 1:
                raise ValueError(f"{name}.taps must be >= 1")
            if mu <= 0:
                raise ValueError(f"{name}.mu must be > 0")
        if name == "cpr":
            n_avg = int(params.get("avg_window", 1))
            test_angles = int(params.get("test_angles", 1))
            if n_avg < 1:
                raise ValueError("cpr.avg_window must be >= 1")
            if test_angles < 1:
                raise ValueError("cpr.test_angles must be >= 1")
        if name == "demap" and "soft" in params and not isinstance(params["soft"], bool):
            raise ValueError("demap.soft must be a boolean when provided")


def run_dsp_chain(spec: SimulationSpec, samples: np.ndarray, blocks: list[DspBlock]) -> DspOutput:
    params: dict[str, Any] = {}
    out = samples
    fs = spec.signal.symbol_rate_baud * spec.runtime.samples_per_symbol
    blocks = resolve_dsp_chain(spec, blocks)
    demap_enabled = False
    demap_soft = False

    for block in blocks:
        if not block.enabled:
            continue
        if block.name not in _DSP_BLOCKS:
            params.setdefault("warnings", []).append(f"Unsupported DSP block: {block.name}")
            continue

        if block.name == "resample":
            out_fs = block.params.get("out_fs_hz", fs)
            res_param = build_resample_params(fs, out_fs)
            out = dsp_core.resample(out, res_param)
            fs = out_fs
            params.setdefault("resample", []).append({"out_fs": out_fs})
        elif block.name == "matched_filter":
            span = 6
            sps = spec.runtime.samples_per_symbol
            t = np.arange(-span / 2, span / 2 + 1 / sps, 1 / sps)
            taps = dsp_core.rrcFilterTaps(t, spec.signal.rolloff, 1.0)
            out = dsp_core.firFilter(taps, out)
            params["matched_filter"] = {"n_taps": int(len(taps))}
        elif block.name == "cd_comp":
            edc_param = build_edc_params(spec)
            out = equalization.edc(out, edc_param)
            params["cd_comp"] = {"edc": True}
        elif block.name == "mimo_eq":
            taps = int(block.params.get("taps", 15))
            mu = float(block.params.get("mu", 1e-3))
            eq_param = build_mimo_eq_params(spec, taps=taps, mu=mu)
            try:
                out = equalization.mimoAdaptEqualizer(out, eq_param)
            except ZeroDivisionError:
                params.setdefault("warnings", []).append(
                    "mimo_eq failed due to division by zero; signal passthrough applied."
                )
                params["mimo_eq"] = {"taps": taps, "mu": mu, "error": "division_by_zero"}
            else:
                params["mimo_eq"] = {"taps": taps, "mu": mu}
        elif block.name == "ffe":
            taps = int(block.params.get("taps", 11))
            mu = float(block.params.get("mu", 1e-3))
            eq_param = build_mimo_eq_params(spec, taps=taps, mu=mu)
            try:
                out = equalization.mimoAdaptEqualizer(out, eq_param)
            except ZeroDivisionError:
                params.setdefault("warnings", []).append(
                    "ffe failed due to division by zero; signal passthrough applied."
                )
                params["ffe"] = {"taps": taps, "mu": mu, "error": "division_by_zero"}
            else:
                params["ffe"] = {"taps": taps, "mu": mu}
        elif block.name == "cpr":
            const_symb = modulation.grayMapping(
                4 if spec.signal.format == "coherent_qpsk" else 4,
                "psk" if spec.signal.format == "coherent_qpsk" else "pam",
            )
            n_avg = int(block.params.get("avg_window", 8))
            test_angles = int(block.params.get("test_angles", 64))
            theta = carrierRecovery.bps(out, n_avg, const_symb, test_angles)
            out = out * np.exp(-1j * theta)
            params["cpr"] = {"avg_window": n_avg, "test_angles": test_angles}
        elif block.name == "demap":
            demap_enabled = True
            demap_soft = bool(block.params.get("soft", False))
            params["demap"] = {"soft": demap_soft}

    symbols = _downsample(out, spec.runtime.samples_per_symbol)
    hard_bits = None
    llrs = None
    if demap_enabled:
        order, const_type = _constellation_params(spec.signal.format)
        hard_bits, llrs = _demap_symbols(symbols, order, const_type, demap_soft)
    return DspOutput(symbols=symbols, params=params, hard_bits=hard_bits, llrs=llrs)


def _downsample(samples: np.ndarray, sps: int) -> np.ndarray:
    if sps <= 1:
        return samples
    offset = int(math.floor(sps / 2))
    return samples[offset::sps]


def _constellation_params(signal_format: str) -> tuple[int, str]:
    if signal_format == "coherent_qpsk":
        return 4, "psk"
    if signal_format == "imdd_ook":
        return 2, "ook"
    return 4, "pam"


def _demap_symbols(
    symbols: np.ndarray, order: int, const_type: str, soft: bool
) -> tuple[np.ndarray, np.ndarray | None]:
    flattened = _flatten_symbols(symbols)
    hard_bits = modulation.demodulateGray(flattened, order, const_type).astype(int)
    if not soft:
        return hard_bits, None

    const_symb = modulation.grayMapping(order, const_type)
    const_symb = dsp_core.pnorm(const_symb)
    bit_map = _build_bit_map(const_symb, order)
    rx_symb = dsp_core.pnorm(flattened)
    sigma2 = _estimate_noise_variance(rx_symb, const_symb)
    px = np.full((order, 1), 1.0 / order)
    llrs = np.asarray(opti_metrics.calcLLR(rx_symb, sigma2, const_symb, bit_map, px))
    if llrs.ndim > 1:
        llrs = llrs.reshape(-1)
    return hard_bits, llrs


def _build_bit_map(const_symb: np.ndarray, order: int) -> np.ndarray:
    bits_per_symbol = int(np.log2(order))
    ind_map = modulation.minEuclid(const_symb, const_symb)
    bit_map = dec2bitarray(ind_map, bits_per_symbol)
    return bit_map.reshape(-1, bits_per_symbol)


def _estimate_noise_variance(rx_symb: np.ndarray, const_symb: np.ndarray) -> float:
    indices = modulation.minEuclid(rx_symb, const_symb)
    decided = const_symb[indices]
    sigma2 = float(np.mean(np.abs(rx_symb - decided) ** 2))
    if not np.isfinite(sigma2) or sigma2 <= 0.0:
        sigma2 = 1e-3
    return sigma2


def _flatten_symbols(symbols: np.ndarray) -> np.ndarray:
    return np.asarray(symbols).reshape(-1)

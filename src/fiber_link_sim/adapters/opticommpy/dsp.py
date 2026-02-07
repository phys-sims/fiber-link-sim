from __future__ import annotations

import math
from typing import Any

import numpy as np
from optic.comm import modulation  # type: ignore[import-untyped]
from optic.dsp import carrierRecovery, equalization  # type: ignore[import-untyped]
from optic.dsp import core as dsp_core

from fiber_link_sim.adapters.opticommpy.param_builders import (
    build_edc_params,
    build_mimo_eq_params,
    build_resample_params,
)
from fiber_link_sim.adapters.opticommpy.types import DspOutput
from fiber_link_sim.data_models.spec_models import DspBlock, SimulationSpec

_DSP_BLOCKS = {
    "resample",
    "matched_filter",
    "cd_comp",
    "mimo_eq",
    "ffe",
    "cpr",
    "demap",
}


def run_dsp_chain(spec: SimulationSpec, samples: np.ndarray, blocks: list[DspBlock]) -> DspOutput:
    params: dict[str, Any] = {}
    out = samples
    fs = spec.signal.symbol_rate_baud * spec.runtime.samples_per_symbol

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
            out = equalization.mimoAdaptEqualizer(out, eq_param)
            params["mimo_eq"] = {"taps": taps, "mu": mu}
        elif block.name == "ffe":
            taps = int(block.params.get("taps", 11))
            mu = float(block.params.get("mu", 1e-3))
            eq_param = build_mimo_eq_params(spec, taps=taps, mu=mu)
            out = equalization.mimoAdaptEqualizer(out, eq_param)
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
            params["demap"] = {"soft": bool(block.params.get("soft", False))}

    symbols = _downsample(out, spec.runtime.samples_per_symbol)
    return DspOutput(symbols=symbols, params=params)


def _downsample(samples: np.ndarray, sps: int) -> np.ndarray:
    if sps <= 1:
        return samples
    offset = int(math.floor(sps / 2))
    return samples[offset::sps]

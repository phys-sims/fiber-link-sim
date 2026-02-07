from __future__ import annotations

import numpy as np
from optic.dsp import core as dsp_core  # type: ignore[import-untyped]
from optic.models import devices  # type: ignore[import-untyped]

from fiber_link_sim.adapters.opticommpy.param_builders import (
    build_lo_params,
    build_pd_params,
    build_resample_params,
)
from fiber_link_sim.adapters.opticommpy.types import RxOutput
from fiber_link_sim.data_models.spec_models import SimulationSpec


def run_rx_frontend(spec: SimulationSpec, signal: np.ndarray, seed: int) -> RxOutput:
    if spec.transceiver.rx.coherent:
        lo_param = build_lo_params(spec, seed, signal.shape[0])
        lo = devices.basicLaserModel(lo_param)
        pd_param = build_pd_params(spec, seed)
        samples = devices.pdmCoherentReceiver(signal, lo, param=pd_param)
        samples, adc_params = apply_adc(spec, samples)
        return RxOutput(
            samples=samples,
            params={"lo_power_dbm": lo_param.P, **adc_params},
        )

    pd_param = build_pd_params(spec, seed)
    current = devices.photodiode(signal, pd_param)
    samples, adc_params = apply_adc(spec, current)
    return RxOutput(
        samples=samples,
        params={"pd_bandwidth_hz": pd_param.B, **adc_params},
    )


def apply_adc(
    spec: SimulationSpec, samples: np.ndarray
) -> tuple[np.ndarray, dict[str, float | bool]]:
    in_fs = spec.signal.symbol_rate_baud * spec.runtime.samples_per_symbol
    out_fs = spec.transceiver.rx.adc.sample_rate_hz
    resampled = samples
    resampled_flag = False
    if not np.isclose(in_fs, out_fs):
        res_param = build_resample_params(in_fs, out_fs)
        resampled = dsp_core.resample(resampled, res_param)
        resampled_flag = True
    quantized, full_scale = quantize_samples(resampled, spec.transceiver.rx.adc.bits)
    return quantized, {
        "adc_sample_rate_hz": float(out_fs),
        "adc_bits": float(spec.transceiver.rx.adc.bits),
        "adc_resampled": resampled_flag,
        "adc_full_scale": float(full_scale),
    }


def quantize_samples(samples: np.ndarray, bits: int) -> tuple[np.ndarray, float]:
    payload = np.asarray(samples)
    if np.iscomplexobj(payload):
        real = np.real(payload)
        imag = np.imag(payload)
        full_scale = _full_scale(real, imag)
        if full_scale == 0.0:
            return payload.astype(np.complex128, copy=True), full_scale
        real_q = _quantize_real(real, bits, full_scale)
        imag_q = _quantize_real(imag, bits, full_scale)
        return real_q + 1j * imag_q, full_scale

    full_scale = _full_scale(payload)
    if full_scale == 0.0:
        return payload.astype(np.float64, copy=True), full_scale
    return _quantize_real(payload, bits, full_scale), full_scale


def _quantize_real(samples: np.ndarray, bits: int, full_scale: float) -> np.ndarray:
    min_v = -full_scale
    max_v = full_scale
    data_2d, squeezed = _as_2d(np.asarray(samples, dtype=np.float64))
    quantized = dsp_core.quantizer(data_2d, nBits=bits, maxV=max_v, minV=min_v)
    if squeezed:
        return quantized.reshape(-1)
    return quantized


def _full_scale(*arrays: np.ndarray) -> float:
    max_abs = 0.0
    for arr in arrays:
        arr_max = float(np.max(np.abs(arr))) if arr.size else 0.0
        max_abs = max(max_abs, arr_max)
    return max_abs


def _as_2d(arr: np.ndarray) -> tuple[np.ndarray, bool]:
    if arr.ndim == 1:
        return arr.reshape(-1, 1), True
    return arr, False

from __future__ import annotations

import numpy as np

from fiber_link_sim.adapters.opticommpy import rx as rx_adapter


def _expected_quantize(values: np.ndarray, bits: int) -> np.ndarray:
    min_v = -1.0
    max_v = 1.0
    delta = (max_v - min_v) / (2**bits - 1)
    levels = min_v + delta * np.arange(2**bits)
    diffs = np.abs(values.reshape(-1, 1) - levels.reshape(1, -1))
    idx = np.argmin(diffs, axis=1)
    return levels[idx]


def test_adc_quantization_levels_match_uniform_grid() -> None:
    samples = np.array([-1.0, -0.7, -0.1, 0.0, 0.3, 0.9, 1.0])
    quantized_4, full_scale_4 = rx_adapter.quantize_samples(samples, bits=4)
    quantized_8, full_scale_8 = rx_adapter.quantize_samples(samples, bits=8)

    assert full_scale_4 == 1.0
    assert full_scale_8 == 1.0

    expected_4 = _expected_quantize(samples, bits=4)
    expected_8 = _expected_quantize(samples, bits=8)

    assert np.allclose(quantized_4, expected_4)
    assert np.allclose(quantized_8, expected_8)

    step_4 = np.min(np.diff(np.unique(quantized_4)))
    step_8 = np.min(np.diff(np.unique(quantized_8)))
    assert step_8 < step_4

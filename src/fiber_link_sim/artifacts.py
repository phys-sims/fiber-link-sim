from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True, slots=True)
class ArtifactPayload:
    name: str
    arrays: dict[str, np.ndarray]


def artifact_root_for_spec(spec_hash: str) -> Path:
    root = Path("artifacts") / spec_hash
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_npz_artifact(artifact_root: Path, payload: ArtifactPayload) -> dict[str, Any]:
    filename = f"{payload.name}.npz"
    path = artifact_root / filename
    arrays = {key: np.asarray(value) for key, value in payload.arrays.items()}
    np.savez_compressed(path, **arrays)  # type: ignore[arg-type]
    return {
        "name": payload.name,
        "type": "npz",
        "ref": f"artifact://{artifact_root.name}/{filename}",
        "mime": "application/octet-stream",
        "bytes": path.stat().st_size,
    }


def compute_psd(signal: np.ndarray, fs_hz: float) -> tuple[np.ndarray, np.ndarray]:
    signal = np.asarray(signal)
    if signal.size == 0:
        return np.array([]), np.array([])
    spectrum = np.fft.fftshift(np.fft.fft(signal))
    power = np.abs(spectrum) ** 2 / max(signal.size, 1)
    psd_db = 10.0 * np.log10(power + 1e-12)
    freqs = np.fft.fftshift(np.fft.fftfreq(signal.size, d=1.0 / fs_hz))
    return freqs, psd_db


def build_eye_traces(
    samples: np.ndarray, sps: int, *, span_symbols: int = 2, max_traces: int = 128
) -> np.ndarray:
    samples = np.asarray(samples)
    if samples.size == 0:
        return np.array([])
    segment_len = int(span_symbols * sps)
    if segment_len <= 0:
        return np.array([])
    n_segments = samples.size // segment_len
    if n_segments <= 0:
        return np.array([])
    n_traces = min(n_segments, max_traces)
    traces = np.zeros((n_traces, segment_len), dtype=np.float64)
    for idx in range(n_traces):
        start = idx * segment_len
        segment = samples[start : start + segment_len]
        traces[idx, :] = np.real(segment)
    return traces


def compute_phase_error(rx_symbols: np.ndarray, tx_symbols: np.ndarray | None) -> np.ndarray:
    rx_symbols = np.asarray(rx_symbols)
    if rx_symbols.size == 0:
        return np.array([])
    if tx_symbols is not None:
        tx_symbols = np.asarray(tx_symbols)
        if tx_symbols.shape == rx_symbols.shape and np.iscomplexobj(rx_symbols):
            return np.angle(rx_symbols * np.conj(tx_symbols)).reshape(-1)
    if np.iscomplexobj(rx_symbols):
        return np.angle(rx_symbols).reshape(-1)
    return np.array([])

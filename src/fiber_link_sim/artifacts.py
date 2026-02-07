from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from phys_pipeline.types import hash_ndarray  # type: ignore[import-untyped]


@dataclass(frozen=True, slots=True)
class ArtifactPayload:
    name: str
    arrays: dict[str, np.ndarray]


@dataclass(frozen=True, slots=True)
class BlobPayload:
    name: str
    array: np.ndarray
    role: str
    units: str | None = None


class ArtifactStore(Protocol):
    def write_blob(self, payload: BlobPayload) -> dict[str, Any]: ...

    def read_blob(self, ref: str) -> np.ndarray: ...

    def save_npz_artifact(self, payload: ArtifactPayload) -> dict[str, Any]: ...

    def save_json_artifact(self, name: str, payload: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(slots=True)
class InMemoryArtifactStore:
    blobs: dict[str, np.ndarray] = field(default_factory=dict)

    def write_blob(self, payload: BlobPayload) -> dict[str, Any]:
        array = np.asarray(payload.array)
        digest = hash_ndarray(array).hex()
        ref = f"blob://memory/{payload.name}-{digest}.npz"
        self.blobs[ref] = array
        return {
            "ref": ref,
            "name": payload.name,
            "type": "npz",
            "mime": "application/octet-stream",
            "bytes": int(array.nbytes),
            "shape": list(array.shape),
            "dtype": str(array.dtype),
            "role": payload.role,
            "units": payload.units,
        }

    def read_blob(self, ref: str) -> np.ndarray:
        return np.asarray(self.blobs[ref])

    def save_npz_artifact(self, payload: ArtifactPayload) -> dict[str, Any]:
        arrays = {key: np.asarray(value) for key, value in payload.arrays.items()}
        ref = f"artifact://memory/{payload.name}.npz"
        self.blobs[ref] = arrays["data"] if "data" in arrays else np.asarray([])
        return {
            "name": payload.name,
            "type": "npz",
            "ref": ref,
            "mime": "application/octet-stream",
            "bytes": int(sum(arr.nbytes for arr in arrays.values())),
        }

    def save_json_artifact(self, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        ref = f"artifact://memory/{name}.json"
        self.blobs[ref] = np.asarray([])
        return {
            "name": name,
            "type": "json",
            "ref": ref,
            "mime": "application/json",
            "bytes": None,
        }


@dataclass(slots=True)
class LocalArtifactStore:
    root: Path

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "blobs").mkdir(parents=True, exist_ok=True)

    def write_blob(self, payload: BlobPayload) -> dict[str, Any]:
        array = np.asarray(payload.array)
        digest = hash_ndarray(array).hex()
        filename = f"{payload.name}-{digest}.npz"
        path = self.root / "blobs" / filename
        np.savez_compressed(path, data=array)
        return {
            "ref": f"blob://{self.root.name}/blobs/{filename}",
            "name": payload.name,
            "type": "npz",
            "mime": "application/octet-stream",
            "bytes": path.stat().st_size,
            "shape": list(array.shape),
            "dtype": str(array.dtype),
            "role": payload.role,
            "units": payload.units,
        }

    def read_blob(self, ref: str) -> np.ndarray:
        relative = ref.replace("blob://", "")
        path = self.root.parent / relative
        with np.load(path) as data:
            return np.asarray(data["data"])

    def save_npz_artifact(self, payload: ArtifactPayload) -> dict[str, Any]:
        filename = f"{payload.name}.npz"
        path = self.root / filename
        arrays = {key: np.asarray(value) for key, value in payload.arrays.items()}
        np.savez_compressed(path, **arrays)  # type: ignore[arg-type]
        return {
            "name": payload.name,
            "type": "npz",
            "ref": f"artifact://{self.root.name}/{filename}",
            "mime": "application/octet-stream",
            "bytes": path.stat().st_size,
        }

    def save_json_artifact(self, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        filename = f"{name}.json"
        path = self.root / filename
        path.write_text(json.dumps(payload, indent=2, sort_keys=True))
        return {
            "name": name,
            "type": "json",
            "ref": f"artifact://{self.root.name}/{filename}",
            "mime": "application/json",
            "bytes": path.stat().st_size,
        }


def artifact_root_for_spec(spec_hash: str, base_dir: Path | None = None) -> Path:
    root_dir = base_dir or Path("artifacts")
    root = root_dir / spec_hash
    root.mkdir(parents=True, exist_ok=True)
    return root


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

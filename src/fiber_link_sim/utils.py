from __future__ import annotations

import hashlib
import json

import numpy as np

from fiber_link_sim.data_models.spec_models import Path, Signal, SimulationSpec


def compute_spec_hash(spec: SimulationSpec) -> str:
    payload = json.dumps(spec.model_dump(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def derive_rng(seed: int, stage_name: str) -> np.random.Generator:
    digest = hashlib.sha256(f"{seed}-{stage_name}".encode()).digest()
    seed_int = int.from_bytes(digest[:8], "big")
    return np.random.default_rng(seed_int)


def total_link_length_m(path: Path) -> float:
    return float(sum(segment.length_m for segment in path.segments))


def bits_per_symbol(signal: Signal) -> int:
    if signal.format == "coherent_qpsk":
        return 2 * signal.n_pol
    if signal.format == "imdd_ook":
        return 1
    return 2

from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from phys_pipeline import (  # type: ignore[import-untyped]
    PipelineStage,
    StageConfig,
    StageResult,
    State,
)
from phys_pipeline.types import hash_ndarray, hash_small  # type: ignore[import-untyped]


@dataclass(slots=True)
class SimulationState(State):
    meta: dict[str, Any] = field(default_factory=dict)
    tx: dict[str, Any] = field(default_factory=dict)
    optical: dict[str, Any] = field(default_factory=dict)
    rx: dict[str, Any] = field(default_factory=dict)
    stats: dict[str, Any] = field(default_factory=dict)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    rng: np.random.Generator | None = None

    def deepcopy(self) -> SimulationState:
        return copy.deepcopy(self)

    def hashable_repr(self) -> bytes:
        h = hashlib.sha256()
        for payload in (self.meta, self.tx, self.optical, self.rx, self.stats):
            h.update(_hash_payload(payload))
        return h.digest()

    def stage_rng(self, stage_name: str) -> np.random.Generator:
        from fiber_link_sim.utils import derive_stage_rng

        seed = int(self.meta.get("seed", 0))
        return derive_stage_rng(seed, stage_name)


class Stage(PipelineStage[SimulationState, StageConfig]):
    name: str = "stage"


def _hash_payload(payload: Any) -> bytes:
    if isinstance(payload, np.ndarray):
        return hash_ndarray(payload)
    if isinstance(payload, dict):
        h = hashlib.sha256()
        for key in sorted(payload.keys()):
            h.update(str(key).encode())
            h.update(_hash_payload(payload[key]))
        return h.digest()
    if isinstance(payload, (list, tuple)):
        h = hashlib.sha256()
        for item in payload:
            h.update(_hash_payload(item))
        return h.digest()
    return hash_small(payload)


__all__ = ["SimulationState", "Stage", "StageConfig", "StageResult"]

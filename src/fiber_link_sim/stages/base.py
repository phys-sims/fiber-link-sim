from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from phys_pipeline import (
    PipelineStage,
    StageConfig,
    StageResult,
    State,
)
from phys_pipeline.types import hash_ndarray, hash_small

import fiber_link_sim._compat  # noqa: F401
from fiber_link_sim.artifacts import ArtifactStore, BlobPayload, InMemoryArtifactStore


@dataclass(slots=True)
class SimulationState(State):
    meta: dict[str, Any] = field(default_factory=dict)
    refs: dict[str, dict[str, Any]] = field(default_factory=dict)
    signals: dict[str, dict[str, str]] = field(default_factory=dict)
    rx: dict[str, Any] = field(default_factory=dict)
    stats: dict[str, Any] = field(default_factory=dict)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    artifact_store: ArtifactStore = field(default_factory=InMemoryArtifactStore)

    def deepcopy(self) -> SimulationState:
        return copy.deepcopy(self)

    def hashable_repr(self) -> bytes:
        h = hashlib.sha256()
        for payload in (self.meta, self.refs, self.signals, self.rx, self.stats):
            h.update(_hash_payload(payload))
        return h.digest()

    def stage_rng(self, stage_name: str) -> np.random.Generator:
        from fiber_link_sim.utils import derive_stage_rng

        seed = int(self.meta.get("seed", 0))
        return derive_stage_rng(seed, stage_name)

    def store_blob(
        self,
        name: str,
        array: np.ndarray,
        *,
        role: str,
        units: str | None = None,
    ) -> str:
        payload = self.artifact_store.write_blob(
            BlobPayload(name=name, array=np.asarray(array), role=role, units=units)
        )
        ref = payload["ref"]
        self.refs[ref] = payload
        return ref

    def store_signal(
        self,
        section: str,
        name: str,
        array: np.ndarray,
        *,
        units: str | None = None,
    ) -> str:
        ref = self.store_blob(name, array, role=f"signal:{section}", units=units)
        self.signals.setdefault(section, {})[name] = ref
        return ref

    def load_ref(self, ref: str) -> np.ndarray:
        return np.asarray(self.artifact_store.read_blob(ref))

    def load_signal(self, section: str, name: str) -> np.ndarray | None:
        ref = self.signals.get(section, {}).get(name)
        if ref is None:
            return None
        return self.load_ref(ref)


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

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import fiber_link_sim._compat  # noqa: F401

from phys_pipeline import (
    CacheConfig,
    DagCache,
    DagExecutor,
    LocalScheduler,
    NodeSpec,
    build_cache_backend,
)

from fiber_link_sim.stages.base import SimulationState


@dataclass(frozen=True, slots=True)
class PipelineExecutionMetadata:
    mode: str
    cache_backend: str | None
    cache_hits: int = 0


def _build_linear_nodes(stages: list[Any]) -> list[NodeSpec]:
    nodes: list[NodeSpec] = []
    for index, stage in enumerate(stages):
        node_id = stage.cfg.name if getattr(stage, "cfg", None) is not None else stage.__class__.__name__
        deps = [nodes[index - 1].id] if index > 0 else []
        nodes.append(NodeSpec(id=node_id, deps=deps, op_name=node_id, version="v2", stage=stage))
    return nodes


def run_pipeline(pipeline: Any, state: SimulationState) -> PipelineExecutionMetadata:
    mode = os.getenv("FIBER_LINK_SIM_PIPELINE_EXECUTOR", "sequential").strip().lower()
    if mode != "dag":
        pipeline.run(state)
        return PipelineExecutionMetadata(mode="sequential", cache_backend=None)

    scheduler = LocalScheduler(
        max_workers=max(1, int(os.getenv("FIBER_LINK_SIM_PIPELINE_MAX_WORKERS", "2"))),
        max_cpu=max(1, int(os.getenv("FIBER_LINK_SIM_PIPELINE_MAX_CPU", "2"))),
        max_gpu=0,
    )
    cache_backend_name = os.getenv("FIBER_LINK_SIM_PIPELINE_CACHE_BACKEND", "disk").strip().lower()
    cache = None
    if cache_backend_name != "none":
        cache_root = Path(os.getenv("FIBER_LINK_SIM_PIPELINE_CACHE_ROOT", ".phys_pipeline_cache"))
        cache_cfg = CacheConfig(backend=cache_backend_name, disk_root=cache_root)
        cache = DagCache(build_cache_backend(cache_cfg))

    executor = DagExecutor(scheduler=scheduler, cache=cache)
    nodes = _build_linear_nodes(pipeline.stages)
    run_result = executor.run(state, nodes)
    final_state = cast(SimulationState, run_result.results[nodes[-1].id].state)
    state.meta = final_state.meta
    state.refs = final_state.refs
    state.signals = final_state.signals
    state.rx = final_state.rx
    state.stats = final_state.stats
    state.artifacts = final_state.artifacts
    state.artifact_store = final_state.artifact_store

    cache_hits = sum(1 for record in run_result.provenance.get("node_runs", []) if record.get("cache_hit"))
    return PipelineExecutionMetadata(mode="dag", cache_backend=cache_backend_name, cache_hits=cache_hits)

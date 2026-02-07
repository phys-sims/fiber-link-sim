from __future__ import annotations

import json
import os
import time
from multiprocessing import get_context
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from fiber_link_sim.data_models.spec_models import (
    Artifact,
    ErrorInfo,
    Provenance,
    SimulationResult,
    SimulationSpec,
    Summary,
)
from fiber_link_sim.pipeline import build_pipeline
from fiber_link_sim.stages.base import SimulationState
from fiber_link_sim.utils import compute_spec_hash, create_root_rng

SIM_VERSION = "0.1.0"
_SIMULATION_CACHE: dict[tuple[str, int], SimulationResult] = {}


def _simulate_worker(spec_payload: dict[str, Any], queue: Any) -> None:
    os.environ["FIBER_LINK_SIM_NO_SUBPROCESS"] = "1"
    result = simulate(spec_payload)
    queue.put(result.model_dump())


def _run_in_subprocess(spec_payload: dict[str, Any]) -> SimulationResult:
    ctx = get_context("spawn")
    queue = ctx.Queue()
    process = ctx.Process(target=_simulate_worker, args=(spec_payload, queue))
    process.start()
    process.join()
    if process.exitcode != 0 or queue.empty():
        return SimulationResult(
            v="v0.2",
            status="error",
            error=ErrorInfo(
                code="runtime_error",
                message="subprocess simulation failed",
                details={"exitcode": process.exitcode},
            ),
            provenance=Provenance(
                sim_version=SIM_VERSION,
                spec_hash="unknown",
                seed=0,
                runtime_s=0.0,
                backend=None,
                model=None,
            ),
        )
    return SimulationResult.model_validate(queue.get())


def _load_spec(spec: dict[str, Any] | str | Path | SimulationSpec) -> SimulationSpec:
    if isinstance(spec, SimulationSpec):
        return spec
    if isinstance(spec, (str, Path)):
        path = Path(spec)
        data = json.loads(path.read_text())
        return SimulationSpec.model_validate(data)
    return SimulationSpec.model_validate(spec)


def simulate(spec: dict[str, Any] | str | Path | SimulationSpec) -> SimulationResult:
    start = time.perf_counter()
    try:
        spec_model = _load_spec(spec)
    except (ValidationError, OSError, json.JSONDecodeError) as exc:
        runtime_s = time.perf_counter() - start
        return SimulationResult(
            v="v0.2",
            status="error",
            error=ErrorInfo(code="validation_error", message=str(exc)),
            provenance=Provenance(
                sim_version=SIM_VERSION,
                spec_hash="invalid",
                seed=0,
                runtime_s=runtime_s,
                backend=None,
                model=None,
            ),
        )

    spec_hash = compute_spec_hash(spec_model)
    cache_key = (spec_hash, spec_model.runtime.seed)
    cached = _SIMULATION_CACHE.get(cache_key)
    if cached is not None:
        return SimulationResult.model_validate(cached.model_dump())

    if spec_model.processing.autotune and spec_model.processing.autotune.enabled:
        runtime_s = time.perf_counter() - start
        return SimulationResult(
            v=spec_model.v,
            status="error",
            error=ErrorInfo(
                code="not_implemented",
                message="processing.autotune.enabled is not implemented",
                details={
                    "budget_trials": spec_model.processing.autotune.budget_trials,
                    "targets": spec_model.processing.autotune.targets,
                },
            ),
            provenance=Provenance(
                sim_version=SIM_VERSION,
                spec_hash=spec_hash,
                seed=spec_model.runtime.seed,
                runtime_s=runtime_s,
                backend=spec_model.propagation.backend,
                model=spec_model.propagation.model,
            ),
        )

    state = SimulationState(
        meta={
            "seed": spec_model.runtime.seed,
            "spec_hash": spec_hash,
            "version": SIM_VERSION,
        },
        rng=create_root_rng(spec_model.runtime.seed),
    )

    pipeline = build_pipeline(spec_model)
    timeout_s = spec_model.runtime.max_runtime_s - (time.perf_counter() - start)
    if timeout_s <= 0:
        runtime_s = time.perf_counter() - start
        return SimulationResult(
            v=spec_model.v,
            status="error",
            error=ErrorInfo(
                code="timeout",
                message="runtime exceeded max_runtime_s before pipeline execution",
                details={
                    "max_runtime_s": spec_model.runtime.max_runtime_s,
                    "elapsed_s": runtime_s,
                },
            ),
            provenance=Provenance(
                sim_version=SIM_VERSION,
                spec_hash=spec_hash,
                seed=spec_model.runtime.seed,
                runtime_s=runtime_s,
                backend=spec_model.propagation.backend,
                model=spec_model.propagation.model,
            ),
            warnings=state.meta.get("warnings", []),
        )

    try:
        pipeline.run(state)
    except Exception as exc:
        if isinstance(exc, SystemError) and not os.environ.get("FIBER_LINK_SIM_NO_SUBPROCESS"):
            return _run_in_subprocess(spec_model.model_dump())
        runtime_s = time.perf_counter() - start
        return SimulationResult(
            v=spec_model.v,
            status="error",
            error=ErrorInfo(
                code="runtime_error",
                message=str(exc),
                details={"exception_type": exc.__class__.__name__},
            ),
            provenance=Provenance(
                sim_version=SIM_VERSION,
                spec_hash=state.meta["spec_hash"],
                seed=spec_model.runtime.seed,
                runtime_s=runtime_s,
                backend=spec_model.propagation.backend,
                model=spec_model.propagation.model,
            ),
            warnings=state.meta.get("warnings", []),
        )

    runtime_s = time.perf_counter() - start
    if runtime_s > spec_model.runtime.max_runtime_s:
        return SimulationResult(
            v=spec_model.v,
            status="error",
            error=ErrorInfo(
                code="timeout",
                message="runtime exceeded max_runtime_s during pipeline execution",
                details={
                    "max_runtime_s": spec_model.runtime.max_runtime_s,
                    "elapsed_s": runtime_s,
                },
            ),
            provenance=Provenance(
                sim_version=SIM_VERSION,
                spec_hash=state.meta["spec_hash"],
                seed=spec_model.runtime.seed,
                runtime_s=runtime_s,
                backend=spec_model.propagation.backend,
                model=spec_model.propagation.model,
            ),
            warnings=state.meta.get("warnings", []),
        )

    warnings = state.meta.get("warnings", [])
    artifacts = state.artifacts
    summary_payload = state.stats.get("summary")
    summary = Summary.model_validate(summary_payload) if summary_payload else None

    result = SimulationResult(
        v=spec_model.v,
        status="success",
        summary=summary,
        provenance=Provenance(
            sim_version=SIM_VERSION,
            spec_hash=spec_hash,
            seed=spec_model.runtime.seed,
            runtime_s=runtime_s,
            backend=spec_model.propagation.backend,
            model=spec_model.propagation.model,
        ),
        warnings=warnings,
        artifacts=[Artifact.model_validate(artifact) for artifact in artifacts],
    )
    _SIMULATION_CACHE[cache_key] = result
    return SimulationResult.model_validate(result.model_dump())

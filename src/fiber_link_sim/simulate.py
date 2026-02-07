from __future__ import annotations

import json
import time
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
            v="v0.1",
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

    state = SimulationState(
        meta={
            "seed": spec_model.runtime.seed,
            "spec_hash": compute_spec_hash(spec_model),
            "version": SIM_VERSION,
        },
        rng=create_root_rng(spec_model.runtime.seed),
    )

    pipeline = build_pipeline(spec_model)
    pipeline.run(state)

    warnings = state.meta.get("warnings", [])
    artifacts = state.artifacts
    summary_payload = state.stats.get("summary")
    summary = Summary.model_validate(summary_payload) if summary_payload else None

    runtime_s = time.perf_counter() - start
    return SimulationResult(
        v=spec_model.v,
        status="success",
        summary=summary,
        provenance=Provenance(
            sim_version=SIM_VERSION,
            spec_hash=state.meta["spec_hash"],
            seed=spec_model.runtime.seed,
            runtime_s=runtime_s,
            backend=spec_model.propagation.backend,
            model=spec_model.propagation.model,
        ),
        warnings=warnings,
        artifacts=[Artifact.model_validate(artifact) for artifact in artifacts],
    )

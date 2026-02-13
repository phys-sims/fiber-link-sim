from __future__ import annotations

from dataclasses import dataclass

from fiber_link_sim.pipeline_execution import run_pipeline
from fiber_link_sim.stages.base import SimulationState, StageConfig, StageResult


@dataclass(slots=True)
class _CounterPipeline:
    stages: list[object]

    def run(self, state: SimulationState) -> None:
        current = state
        for stage in self.stages:
            current = stage.process(current).state
        state.meta = current.meta
        state.refs = current.refs
        state.signals = current.signals
        state.rx = current.rx
        state.stats = current.stats
        state.artifacts = current.artifacts
        state.artifact_store = current.artifact_store


class _CounterStage:
    def __init__(self, name: str, increment: int):
        self.cfg = StageConfig(name=name)
        self._increment = increment

    def process(self, state: SimulationState, **_: object) -> StageResult[SimulationState]:
        next_state = state.deepcopy()
        next_state.stats["counter"] = int(next_state.stats.get("counter", 0)) + self._increment
        return StageResult(state=next_state)


def _build_pipeline() -> _CounterPipeline:
    return _CounterPipeline(stages=[_CounterStage("tx", 1), _CounterStage("metrics", 2)])


def test_dag_executor_with_cache_reports_cache_hits(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FIBER_LINK_SIM_PIPELINE_EXECUTOR", "dag")
    monkeypatch.setenv("FIBER_LINK_SIM_PIPELINE_CACHE_BACKEND", "disk")
    monkeypatch.setenv("FIBER_LINK_SIM_PIPELINE_CACHE_ROOT", str(tmp_path / "dag-cache"))

    pipeline = _build_pipeline()
    first_state = SimulationState(meta={"seed": 7})
    first = run_pipeline(pipeline, first_state)

    second_state = SimulationState(meta={"seed": 7})
    second = run_pipeline(pipeline, second_state)

    assert first.mode == "dag"
    assert first.cache_hits == 0
    assert second.cache_hits == 2
    assert second_state.stats["counter"] == 3


def test_dag_and_sequential_execution_match(monkeypatch, tmp_path) -> None:
    pipeline = _build_pipeline()

    seq_state = SimulationState(meta={"seed": 11})
    monkeypatch.setenv("FIBER_LINK_SIM_PIPELINE_EXECUTOR", "sequential")
    seq_meta = run_pipeline(pipeline, seq_state)

    dag_state = SimulationState(meta={"seed": 11})
    monkeypatch.setenv("FIBER_LINK_SIM_PIPELINE_EXECUTOR", "dag")
    monkeypatch.setenv("FIBER_LINK_SIM_PIPELINE_CACHE_BACKEND", "none")
    monkeypatch.setenv("FIBER_LINK_SIM_PIPELINE_CACHE_ROOT", str(tmp_path / "dag-cache"))
    dag_meta = run_pipeline(pipeline, dag_state)

    assert seq_meta.mode == "sequential"
    assert dag_meta.mode == "dag"
    assert seq_state.stats == dag_state.stats

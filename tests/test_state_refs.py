from __future__ import annotations

from pathlib import Path

import numpy as np

from fiber_link_sim.artifacts import LocalArtifactStore, artifact_root_for_spec
from fiber_link_sim.stages.base import SimulationState


def _build_state(
    root: Path, *, seed: int, waveform: np.ndarray, symbols: np.ndarray
) -> SimulationState:
    store = LocalArtifactStore(artifact_root_for_spec("spec", base_dir=root))
    state = SimulationState(meta={"seed": seed}, artifact_store=store)
    state.store_signal("tx", "waveform", waveform)
    state.store_signal("tx", "symbols", symbols)
    return state


def test_state_hash_stable_with_refs(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    waveform = np.zeros(8)
    symbols = np.array([1 + 1j, -1 - 1j])

    state_a = _build_state(root, seed=1, waveform=waveform, symbols=symbols)
    state_b = _build_state(root, seed=1, waveform=waveform, symbols=symbols)
    assert state_a.hashable_repr() == state_b.hashable_repr()

    state_c = _build_state(root, seed=1, waveform=waveform + 1.0, symbols=symbols)
    assert state_a.hashable_repr() != state_c.hashable_repr()


def test_stage_rng_independent_of_call_order() -> None:
    state = SimulationState(meta={"seed": 123})
    first = int(state.stage_rng("tx").integers(0, 2**31 - 1))
    second = int(state.stage_rng("channel").integers(0, 2**31 - 1))

    state_reordered = SimulationState(meta={"seed": 123})
    second_reordered = int(state_reordered.stage_rng("channel").integers(0, 2**31 - 1))
    first_reordered = int(state_reordered.stage_rng("tx").integers(0, 2**31 - 1))

    assert first == first_reordered
    assert second == second_reordered

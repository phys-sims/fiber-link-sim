from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from fiber_link_sim.artifacts import LocalArtifactStore, artifact_root_for_spec
from fiber_link_sim.data_models.spec_models import SimulationSpec
from fiber_link_sim.data_models.stage_models import ArtifactsSpecSlice
from fiber_link_sim.stages.base import SimulationState
from fiber_link_sim.stages.configs import ArtifactsStageConfig
from fiber_link_sim.stages.core import ArtifactsStage
from fiber_link_sim.utils import compute_spec_hash

EXAMPLE_DIR = Path(__file__).resolve().parents[1] / "src/fiber_link_sim/schema/examples"


def _load_example(name: str) -> dict:
    return json.loads((EXAMPLE_DIR / name).read_text())


def _build_state(spec: SimulationSpec, *, root: Path) -> SimulationState:
    store = LocalArtifactStore(artifact_root_for_spec(compute_spec_hash(spec), base_dir=root))
    state = SimulationState(
        meta={"seed": spec.runtime.seed, "spec_hash": compute_spec_hash(spec)},
        artifact_store=store,
    )
    state.store_signal("tx", "waveform", np.zeros(16))
    state.store_signal("tx", "symbols", np.array([1 + 1j, -1 - 1j, 1 - 1j, -1 + 1j]))
    state.store_signal("optical", "waveform", np.ones(16))
    state.store_signal("rx", "samples", np.full(16, 2.0))
    state.store_signal("rx", "dsp_samples", np.full(16, 1.0))
    state.store_signal("rx", "symbols", np.array([1 + 1j, -1 - 1j, 1 - 1j, -1 + 1j]))
    return state


def test_artifacts_absent_when_level_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    spec_data = _load_example("ook_smoke.json")
    spec_data["outputs"]["artifact_level"] = "none"
    spec_data["outputs"]["return_waveforms"] = True
    spec = SimulationSpec.model_validate(spec_data)

    state = _build_state(spec, root=tmp_path / "artifacts")
    stage = ArtifactsStage(
        cfg=ArtifactsStageConfig(name="artifacts", spec=ArtifactsSpecSlice.from_spec(spec))
    )
    stage.process(state)

    assert state.artifacts == []


def test_waveform_refs_present_when_requested(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    spec_data = _load_example("ook_smoke.json")
    spec_data["outputs"]["artifact_level"] = "basic"
    spec_data["outputs"]["return_waveforms"] = True
    spec = SimulationSpec.model_validate(spec_data)

    state = _build_state(spec, root=tmp_path / "artifacts")
    stage = ArtifactsStage(
        cfg=ArtifactsStageConfig(name="artifacts", spec=ArtifactsSpecSlice.from_spec(spec))
    )
    stage.process(state)

    names = {artifact["name"] for artifact in state.artifacts}
    assert names == {
        "channel_psd",
        "dsp_constellation",
        "dsp_eye",
        "dsp_phase_error",
        "optical_waveform",
        "rx_eye",
        "rx_samples",
        "tx_psd",
        "tx_waveform",
    }

    for artifact in state.artifacts:
        ref = artifact["ref"]
        assert isinstance(ref, str)
        path = tmp_path / "artifacts" / compute_spec_hash(spec) / f"{artifact['name']}.npz"
        assert path.exists()


def test_artifacts_absent_when_waveforms_disabled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    spec_data = _load_example("ook_smoke.json")
    spec_data["outputs"]["artifact_level"] = "basic"
    spec_data["outputs"]["return_waveforms"] = False
    spec = SimulationSpec.model_validate(spec_data)

    state = _build_state(spec, root=tmp_path / "artifacts")
    stage = ArtifactsStage(
        cfg=ArtifactsStageConfig(name="artifacts", spec=ArtifactsSpecSlice.from_spec(spec))
    )
    stage.process(state)

    assert state.artifacts == []

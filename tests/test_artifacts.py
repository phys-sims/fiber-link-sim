from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from fiber_link_sim.data_models.spec_models import SimulationSpec
from fiber_link_sim.stages.base import SimulationState
from fiber_link_sim.stages.configs import ArtifactsStageConfig
from fiber_link_sim.stages.core import ArtifactsStage
from fiber_link_sim.utils import compute_spec_hash

EXAMPLE_DIR = Path(__file__).resolve().parents[1] / "src/fiber_link_sim/schema/examples"


def _load_example(name: str) -> dict:
    return json.loads((EXAMPLE_DIR / name).read_text())


def _build_state(spec: SimulationSpec) -> SimulationState:
    state = SimulationState(
        meta={"seed": spec.runtime.seed, "spec_hash": compute_spec_hash(spec)},
    )
    state.tx["waveform"] = np.zeros(16)
    state.tx["symbols"] = np.array([1 + 1j, -1 - 1j, 1 - 1j, -1 + 1j])
    state.optical["waveform"] = np.ones(16)
    state.rx["samples"] = np.full(16, 2.0)
    state.rx["dsp_samples"] = np.full(16, 1.0)
    state.rx["symbols"] = np.array([1 + 1j, -1 - 1j, 1 - 1j, -1 + 1j])
    return state


def test_artifacts_absent_when_level_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    spec_data = _load_example("ook_smoke.json")
    spec_data["outputs"]["artifact_level"] = "none"
    spec_data["outputs"]["return_waveforms"] = True
    spec = SimulationSpec.model_validate(spec_data)

    state = _build_state(spec)
    stage = ArtifactsStage(cfg=ArtifactsStageConfig(spec=spec))
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

    state = _build_state(spec)
    stage = ArtifactsStage(cfg=ArtifactsStageConfig(spec=spec))
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

    state = _build_state(spec)
    stage = ArtifactsStage(cfg=ArtifactsStageConfig(spec=spec))
    stage.process(state)

    assert state.artifacts == []

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

from fiber_link_sim.artifacts import artifact_root_for_spec
from fiber_link_sim.data_models.spec_models import SimulationSpec
from fiber_link_sim.simulate import simulate

REPO_ROOT = Path(__file__).resolve().parents[2]

EXAMPLE_DIR = REPO_ROOT / "src/fiber_link_sim/schema/examples"


@pytest.mark.integration
def test_qpsk_story_manifest_structure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    spec_payload = json.loads((EXAMPLE_DIR / "qpsk_longhaul_1span.json").read_text())
    spec_payload["runtime"]["n_symbols"] = 512
    spec_payload["runtime"]["samples_per_symbol"] = 2
    spec_payload["propagation"]["effects"] = {
        "dispersion": False,
        "nonlinearity": False,
        "ase": False,
        "pmd": False,
        "env_effects": False,
    }
    spec_payload["propagation"]["ssfm"]["dz_m"] = spec_payload["path"]["segments"][0]["length_m"]
    spec_payload["spans"]["amplifier"] = {"type": "none", "mode": "none"}
    spec_payload["processing"]["fec"] = {
        "enabled": False,
        "scheme": "none",
        "code_rate": 1.0,
        "params": {},
    }
    spec_payload["outputs"]["artifact_level"] = "debug"
    spec_payload["outputs"]["return_waveforms"] = True

    result = simulate(spec_payload)
    assert result.status == "success"

    spec_model = SimulationSpec.model_validate(spec_payload)
    output_root = tmp_path / "story"
    output_root.mkdir(parents=True, exist_ok=True)
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    generate_story_assets = importlib.import_module(
        "scripts.generate_qpsk_story"
    ).generate_story_assets
    manifest = generate_story_assets(
        spec_model=spec_model,
        result=result.model_dump(),
        artifact_root=artifact_root_for_spec(result.provenance.spec_hash),
        output_root=output_root,
    )

    assert manifest["version"] == "v1"
    assert manifest["spec_hash"] == result.provenance.spec_hash
    assert "stages" in manifest
    assert "artifacts" in manifest
    assert manifest["summary"]["latency_s"]["total_s"] >= 0.0

    for artifact in manifest["artifacts"]:
        assert Path(artifact["path"]).exists()
        assert artifact["path"].endswith((".svg", ".json"))

from __future__ import annotations

import importlib
import json
import re
import time
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest

from fiber_link_sim.adapters.opticommpy.stages import ADAPTERS
from fiber_link_sim.adapters.opticommpy.types import TxOutput
from fiber_link_sim.data_models.spec_models import SimulationResult, SimulationSpec
from fiber_link_sim.simulate import simulate
from fiber_link_sim.utils import compute_spec_hash

simulate_module = importlib.import_module("fiber_link_sim.simulate")

EXAMPLE_DIR = Path("src/fiber_link_sim/schema/examples")
PYPROJECT_FILE = Path("pyproject.toml")


def _load_example(name: str) -> dict:
    return json.loads((EXAMPLE_DIR / name).read_text())


def test_example_specs_validate() -> None:
    for filename in (
        "qpsk_longhaul_manakov.json",
        "qpsk_longhaul_1span.json",
        "qpsk_longhaul_multispan.json",
        "ook_smoke.json",
        "pam4_shorthaul.json",
        "hft_chicago_new_jersey.json",
        "hft_london_frankfurt.json",
        "hft_new_york_london.json",
    ):
        spec_data = _load_example(filename)
        spec = SimulationSpec.model_validate(spec_data)
        assert spec.v == "0.2"


def test_sim_version_matches_package_release_version() -> None:
    pyproject_text = PYPROJECT_FILE.read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject_text, flags=re.MULTILINE)
    assert match is not None
    project_version = match.group(1)
    spec_data = _load_example("ook_smoke.json")

    result = simulate(spec_data)

    assert simulate_module.SIM_VERSION == project_version
    assert result.provenance.sim_version == project_version


@pytest.mark.integration
@pytest.mark.opticommpy
@pytest.mark.slow
def test_simulation_results_validate() -> None:
    for filename in (
        "qpsk_longhaul_manakov.json",
        "qpsk_longhaul_1span.json",
        "qpsk_longhaul_multispan.json",
        "ook_smoke.json",
        "pam4_shorthaul.json",
    ):
        spec_data = _load_example(filename)
        result = simulate(spec_data)
        assert result.status == "success"
        SimulationResult.model_validate(result.model_dump())


@pytest.mark.integration
@pytest.mark.opticommpy
def test_simulation_runtime_error_returns_structured_result(monkeypatch: Any) -> None:
    spec_data = _load_example("ook_smoke.json")
    spec = SimulationSpec.model_validate(spec_data)

    def _broken_tx_run(self: Any, spec: SimulationSpec, seed: int) -> TxOutput:
        return TxOutput(signal=None, symbols=np.array([]), params=cast(Any, {}))

    monkeypatch.setattr(type(ADAPTERS.tx), "run", _broken_tx_run)
    simulate_module._SIMULATION_CACHE.clear()

    result = simulate(spec_data)

    assert result.status == "error"
    assert result.summary is None
    assert result.error is not None
    assert result.error.code == "runtime_error"
    assert "missing tx waveform" in result.error.message
    assert result.error.details["exception_type"] == "ValueError"
    assert result.provenance.seed == spec.runtime.seed
    assert result.provenance.spec_hash == compute_spec_hash(spec)
    assert result.provenance.runtime_s >= 0
    SimulationResult.model_validate(result.model_dump())


def test_simulation_timeout_returns_structured_result(monkeypatch: Any) -> None:
    spec_data = _load_example("ook_smoke.json")
    spec_data["runtime"]["max_runtime_s"] = 0.05
    spec = SimulationSpec.model_validate(spec_data)

    class _SlowPipeline:
        def run(self, state: Any) -> None:
            time.sleep(0.2)

    monkeypatch.setattr(simulate_module, "build_pipeline", lambda _: _SlowPipeline())

    result = simulate(spec_data)

    assert result.status == "error"
    assert result.summary is None
    assert result.error is not None
    assert result.error.code == "timeout"
    assert result.provenance.seed == spec.runtime.seed
    assert result.provenance.spec_hash == compute_spec_hash(spec)
    assert result.provenance.runtime_s >= 0
    SimulationResult.model_validate(result.model_dump())

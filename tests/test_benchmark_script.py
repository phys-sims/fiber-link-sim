from __future__ import annotations

import os

from fiber_link_sim.benchmarking import env_overrides


def test_env_overrides_restores_values(monkeypatch) -> None:
    monkeypatch.setenv("FIBER_LINK_SIM_PIPELINE_EXECUTOR", "sequential")

    with env_overrides(
        {
            "FIBER_LINK_SIM_PIPELINE_EXECUTOR": "dag",
            "FIBER_LINK_SIM_PIPELINE_CACHE_BACKEND": "none",
        }
    ):
        assert os.environ["FIBER_LINK_SIM_PIPELINE_EXECUTOR"] == "dag"
        assert os.environ["FIBER_LINK_SIM_PIPELINE_CACHE_BACKEND"] == "none"

    assert os.environ["FIBER_LINK_SIM_PIPELINE_EXECUTOR"] == "sequential"
    assert "FIBER_LINK_SIM_PIPELINE_CACHE_BACKEND" not in os.environ

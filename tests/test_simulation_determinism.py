from __future__ import annotations

import json
from math import isclose
from pathlib import Path

import pytest

from fiber_link_sim.simulate import simulate

EXAMPLE_DIR = Path("src/fiber_link_sim/schema/examples")


@pytest.mark.integration
@pytest.mark.opticommpy
@pytest.mark.slow
def test_simulation_determinism() -> None:
    spec = json.loads((EXAMPLE_DIR / "qpsk_longhaul_manakov.json").read_text())
    result_a = simulate(spec)
    result_b = simulate(spec)
    assert result_a.status == "success"
    assert result_b.status == "success"
    assert result_a.summary is not None
    assert result_b.summary is not None
    assert result_a.provenance is not None
    assert result_b.provenance is not None
    assert result_a.provenance.seed == result_b.provenance.seed
    assert isclose(result_a.summary.latency_s.total, result_b.summary.latency_s.total)
    assert isclose(
        result_a.summary.throughput_bps.net_after_fec, result_b.summary.throughput_bps.net_after_fec
    )
    assert isclose(result_a.summary.errors.pre_fec_ber, result_b.summary.errors.pre_fec_ber)
    assert isclose(result_a.summary.snr_db, result_b.summary.snr_db)

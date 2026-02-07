from __future__ import annotations

import json
from math import isfinite
from pathlib import Path

from fiber_link_sim.simulate import simulate

EXAMPLE_DIR = Path("src/fiber_link_sim/schema/examples")


def _load_example(name: str) -> dict:
    return json.loads((EXAMPLE_DIR / name).read_text())


def test_simulation_examples_success() -> None:
    for filename in (
        "qpsk_longhaul_manakov.json",
        "ook_smoke.json",
        "pam4_shorthaul.json",
    ):
        result = simulate(_load_example(filename))
        assert result.status == "success"
        assert result.summary is not None
        assert isfinite(result.summary.latency_s.total)
        assert 0.0 <= result.summary.errors.pre_fec_ber <= 1.0
        assert 0.0 <= result.summary.errors.post_fec_ber <= 1.0
        assert 0.0 <= result.summary.errors.fer <= 1.0

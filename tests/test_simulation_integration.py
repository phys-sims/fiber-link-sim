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
        "qpsk_longhaul_1span.json",
        "qpsk_longhaul_multispan.json",
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


def test_qpsk_longhaul_expected_ranges() -> None:
    """Document expected BER and OSNR/SNR proxy ranges for QPSK examples."""
    expectations = {
        "qpsk_longhaul_1span.json": {
            "pre_fec_ber": (0.1, 0.25),
            "snr_db": (-1.0, 1.0),
            "osnr_db": (13.0, 18.0),
        },
        "qpsk_longhaul_multispan.json": {
            "pre_fec_ber": (0.1, 0.25),
            "snr_db": (-1.0, 1.0),
            "osnr_db": (13.0, 18.0),
        },
    }
    for filename, bounds in expectations.items():
        result = simulate(_load_example(filename))
        assert result.status == "success"
        assert result.summary is not None
        pre_fec_ber = result.summary.errors.pre_fec_ber
        assert bounds["pre_fec_ber"][0] <= pre_fec_ber <= bounds["pre_fec_ber"][1]

        snr_db = result.summary.snr_db
        assert bounds["snr_db"][0] <= snr_db <= bounds["snr_db"][1]

        osnr_db = result.summary.osnr_db
        assert osnr_db is not None
        assert bounds["osnr_db"][0] <= osnr_db <= bounds["osnr_db"][1]

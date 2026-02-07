from __future__ import annotations

import copy
import json
from math import isfinite
from pathlib import Path

import pytest

from fiber_link_sim.simulate import simulate

EXAMPLE_DIR = Path("src/fiber_link_sim/schema/examples")


def _load_example(name: str) -> dict:
    return json.loads((EXAMPLE_DIR / name).read_text())


@pytest.mark.integration
@pytest.mark.opticommpy
@pytest.mark.slow
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


@pytest.mark.integration
@pytest.mark.opticommpy
@pytest.mark.slow
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


@pytest.mark.integration
@pytest.mark.opticommpy
@pytest.mark.slow
def test_qpsk_longhaul_effects_toggle_impact() -> None:
    base = _load_example("qpsk_longhaul_manakov.json")
    spec_off = copy.deepcopy(base)
    spec_off["propagation"]["effects"] = {
        "dispersion": False,
        "nonlinearity": False,
        "ase": False,
        "pmd": False,
        "env_effects": False,
    }

    spec_on = copy.deepcopy(base)
    spec_on["propagation"]["effects"] = {
        "dispersion": True,
        "nonlinearity": True,
        "ase": True,
        "pmd": True,
        "env_effects": True,
    }

    result_off = simulate(spec_off)
    result_on = simulate(spec_on)

    assert result_off.status == "success"
    assert result_on.status == "success"
    assert result_off.summary is not None
    assert result_on.summary is not None

    assert result_off.summary.errors.pre_fec_ber <= result_on.summary.errors.pre_fec_ber
    assert result_off.summary.osnr_db is None
    assert result_on.summary.osnr_db is not None
    assert isfinite(result_on.summary.osnr_db)

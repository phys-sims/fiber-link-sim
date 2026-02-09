from __future__ import annotations

from math import erfc, sqrt

from fiber_link_sim.metrics import ber_from_snr_linear


def test_awgn_qpsk_ber_matches_closed_form() -> None:
    snr_linear = 10.0
    expected = 0.5 * erfc(sqrt(snr_linear))
    observed = ber_from_snr_linear("coherent_qpsk", snr_linear)
    assert abs(observed - expected) < 1e-12

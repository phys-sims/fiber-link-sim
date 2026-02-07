from __future__ import annotations

from math import erfc, sqrt

from fiber_link_sim.data_models.spec_models import SignalFormat


def snr_from_osnr_db(osnr_db: float, *, coherent: bool) -> float:
    penalty = 3.0 if coherent else 6.0
    return osnr_db - penalty


def evm_from_snr_linear(snr_linear: float) -> float:
    return 1.0 / max(sqrt(snr_linear), 1e-6)


def ber_from_snr_linear(signal_format: SignalFormat, snr_linear: float) -> float:
    snr_linear = max(snr_linear, 1e-9)
    if signal_format == "coherent_qpsk":
        return 0.5 * erfc(sqrt(snr_linear))
    if signal_format == "imdd_ook":
        return 0.5 * erfc(sqrt(snr_linear / 2.0))
    # imdd_pam4
    return 1.5 * 0.5 * erfc(sqrt(snr_linear / 5.0))

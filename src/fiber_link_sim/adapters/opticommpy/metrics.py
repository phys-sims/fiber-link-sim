from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from optic.comm import metrics as opti_metrics  # type: ignore[import-untyped]

from fiber_link_sim.data_models.spec_models import Signal


@dataclass(frozen=True)
class MetricsOutput:
    pre_fec_ber: float
    snr_db: float
    evm_rms: float


def compute_metrics(symb_rx: np.ndarray, symb_tx: np.ndarray, signal: Signal) -> MetricsOutput:
    const_type = _const_type(signal)
    order = _const_order(signal)
    rx_aligned, tx_aligned = _align_symbols(symb_rx, symb_tx)
    evm = opti_metrics.calcEVM(rx_aligned, order, const_type, tx_aligned)
    evm_mean = float(np.mean(evm))
    if not np.isfinite(evm_mean):
        evm_mean = 1.0
    snr_linear = 1.0 / max(evm_mean, 1e-12)
    snr_db = 10.0 * float(np.log10(snr_linear))

    try:
        ber, _, snr = opti_metrics.fastBERcalc(rx_aligned, tx_aligned, order, const_type)
        pre_fec_ber = float(np.mean(ber))
        snr_db = float(np.mean(snr))
        if not np.isfinite(pre_fec_ber) or not np.isfinite(snr_db):
            raise ValueError("non-finite BER/SNR from fastBERcalc")
    except Exception:
        bits_per_symbol = float(np.log2(order))
        ebn0_db = snr_db - 10.0 * float(np.log10(bits_per_symbol))
        theory_const = "pam" if const_type == "ook" else const_type
        pre_fec_ber = float(opti_metrics.theoryBER(order, ebn0_db, theory_const))

    return MetricsOutput(
        pre_fec_ber=pre_fec_ber,
        snr_db=snr_db,
        evm_rms=float(np.sqrt(evm_mean)),
    )


def _const_type(signal: Signal) -> str:
    if signal.format == "coherent_qpsk":
        return "psk"
    if signal.format == "imdd_ook":
        return "ook"
    return "pam"


def _const_order(signal: Signal) -> int:
    if signal.format == "imdd_ook":
        return 2
    return 4


def _align_symbols(symb_rx: np.ndarray, symb_tx: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rx = _as_2d(symb_rx)
    tx = _as_2d(symb_tx)
    n = min(rx.shape[0], tx.shape[0])
    return rx[:n, :], tx[:n, :]


def _as_2d(arr: np.ndarray) -> np.ndarray:
    if arr.ndim == 1:
        return arr.reshape(-1, 1)
    return arr

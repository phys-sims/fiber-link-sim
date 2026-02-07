from __future__ import annotations

import numpy as np
from optic.models import tx as opti_tx  # type: ignore[import-untyped]

from fiber_link_sim.adapters.opticommpy.param_builders import build_tx_params
from fiber_link_sim.adapters.opticommpy.types import TxOutput
from fiber_link_sim.data_models.stage_models import TxSpecSlice
from fiber_link_sim.utils import preserve_numpy_random_state


def run_tx(spec: TxSpecSlice, seed: int) -> TxOutput:
    if spec.signal.format == "coherent_qpsk":
        param = build_tx_params(spec, seed, "coherent")
        with preserve_numpy_random_state(seed):
            signal, symbols, param_out = opti_tx.simpleWDMTx(param)
        return TxOutput(signal=signal, symbols=symbols, params=param_out)

    param = build_tx_params(spec, seed, "pam")
    with preserve_numpy_random_state(seed):
        signal, symbols, param_out = opti_tx.pamTransmitter(param)
    if isinstance(param_out, np.ndarray):
        raise ValueError("unexpected PAM transmitter output signature")
    return TxOutput(signal=signal, symbols=symbols, params=param_out)

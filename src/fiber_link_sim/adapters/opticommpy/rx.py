from __future__ import annotations

import numpy as np
from optic.models import devices  # type: ignore[import-untyped]

from fiber_link_sim.adapters.opticommpy.param_builders import build_lo_params, build_pd_params
from fiber_link_sim.adapters.opticommpy.types import RxOutput
from fiber_link_sim.data_models.spec_models import SimulationSpec


def run_rx_frontend(spec: SimulationSpec, signal: np.ndarray, seed: int) -> RxOutput:
    if spec.transceiver.rx.coherent:
        lo_param = build_lo_params(spec, seed, signal.shape[0])
        lo = devices.basicLaserModel(lo_param)
        pd_param = build_pd_params(spec, seed)
        samples = devices.pdmCoherentReceiver(signal, lo, param=pd_param)
        return RxOutput(samples=samples, params={"lo_power_dbm": lo_param.P})

    pd_param = build_pd_params(spec, seed)
    current = devices.photodiode(signal, pd_param)
    return RxOutput(samples=current, params={"pd_bandwidth_hz": pd_param.B})

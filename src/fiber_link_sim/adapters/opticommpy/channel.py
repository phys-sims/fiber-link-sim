from __future__ import annotations

import math

from optic.comm import metrics as opti_metrics  # type: ignore[import-untyped]
from optic.models import channels  # type: ignore[import-untyped]

from fiber_link_sim.adapters.opticommpy.param_builders import build_channel_params
from fiber_link_sim.adapters.opticommpy.types import ChannelOutput
from fiber_link_sim.data_models.spec_models import SimulationSpec


def run_channel(spec: SimulationSpec, signal: object, seed: int) -> ChannelOutput:
    param, layout = build_channel_params(spec, seed)

    if spec.signal.format == "coherent_qpsk":
        out = channels.manakovSSF(signal, param)
    else:
        out = channels.ssfm(signal, param)

    if isinstance(out, tuple):
        signal_out, params = out
    else:
        signal_out = out
        params = param

    osnr_db = None
    if spec.spans.amplifier.type == "edfa":
        osnr_lin = opti_metrics.calcLinOSNR(
            layout.n_spans,
            10 ** (spec.transceiver.tx.launch_power_dbm / 10) * 1e-3,
            spec.fiber.alpha_db_per_km,
            layout.span_length_km,
            40.0,
            NF=spec.spans.amplifier.noise_figure_db or 0.0,
            Fc=param.Fc,
        )
        osnr_value = float(getattr(osnr_lin, "mean", lambda: osnr_lin)())
        osnr_db = 10.0 * math.log10(osnr_value)

    return ChannelOutput(
        signal=signal_out,
        params=params,
        osnr_db=osnr_db,
        n_spans=layout.n_spans,
    )

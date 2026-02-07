from __future__ import annotations

import numpy as np
from optic.comm import metrics as opti_metrics  # type: ignore[import-untyped]
from optic.models import channels  # type: ignore[import-untyped]

from fiber_link_sim.adapters.opticommpy import units
from fiber_link_sim.adapters.opticommpy.param_builders import build_channel_params
from fiber_link_sim.adapters.opticommpy.types import ChannelOutput
from fiber_link_sim.data_models.stage_models import ChannelSpecSlice
from fiber_link_sim.utils import preserve_numpy_random_state


def run_channel(spec: ChannelSpecSlice, signal: object, seed: int) -> ChannelOutput:
    param, layout = build_channel_params(spec, seed)

    with preserve_numpy_random_state(seed):
        if spec.signal.format == "coherent_qpsk":
            out = channels.manakovSSF(signal, param)
        else:
            out = channels.ssfm(signal, param)

    if isinstance(out, tuple):
        signal_out, params = out
    else:
        signal_out = out
        params = param

    amp_gain_db = getattr(param, "amp_gain_db", None)
    span_loss_db = getattr(param, "span_loss_db", None)
    if amp_gain_db is not None and span_loss_db is not None and param.amp in {"edfa", "ideal"}:
        delta_db = (amp_gain_db - span_loss_db) * layout.n_spans
        if abs(delta_db) > 1e-9:
            signal_out = np.asarray(signal_out) * 10 ** (delta_db / 20)

    osnr_db = None
    if spec.spans.amplifier.type == "edfa" and spec.propagation.effects.ase:
        osnr_lin = opti_metrics.calcLinOSNR(
            layout.n_spans,
            units.dbm_to_watts(spec.transceiver.tx.launch_power_dbm),
            spec.fiber.alpha_db_per_km,
            layout.span_length_km,
            40.0,
            NF=spec.spans.amplifier.noise_figure_db or 0.0,
            Fc=param.Fc,
        )
        osnr_value = float(getattr(osnr_lin, "mean", lambda: osnr_lin)())
        osnr_db = units.linear_to_db(osnr_value)

    return ChannelOutput(
        signal=signal_out,
        params=params,
        osnr_db=osnr_db,
        n_spans=layout.n_spans,
    )

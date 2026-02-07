from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from optic.utils import parameters  # type: ignore[import-untyped]

from fiber_link_sim.adapters.opticommpy import units
from fiber_link_sim.data_models.stage_models import (
    ChannelSpecSlice,
    DspSpecSlice,
    RxFrontEndSpecSlice,
    TxSpecSlice,
)
from fiber_link_sim.utils import total_link_length_m


@dataclass(frozen=True)
class ChannelLayout:
    total_length_km: float
    span_length_km: float
    n_spans: int


def _channel_layout(spec: ChannelSpecSlice) -> ChannelLayout:
    total_length_km = total_link_length_m(spec.path) / 1000.0
    if spec.spans.mode == "from_path_segments":
        n_spans = max(len(spec.path.segments), 1)
        span_length_km = total_length_km / n_spans if n_spans > 0 else total_length_km
    else:
        span_length_km = spec.spans.span_length_m / 1000.0
        n_spans = max(1, int(round(total_length_km / span_length_km)))
    return ChannelLayout(
        total_length_km=total_length_km,
        span_length_km=span_length_km,
        n_spans=n_spans,
    )


def _beta2_to_dispersion(beta2_s2_per_m: float, fc_hz: float) -> float:
    wavelength_m = units.wavelength_m(fc_hz)
    dispersion_s_per_m2 = -(2.0 * np.pi * units.C_M_S / (wavelength_m**2)) * beta2_s2_per_m
    return dispersion_s_per_m2 * 1e6


def _span_loss_db(spec: ChannelSpecSlice, layout: ChannelLayout) -> float:
    return spec.fiber.alpha_db_per_km * layout.span_length_km


def _amplifier_gain_db(spec: ChannelSpecSlice, span_loss_db: float) -> float:
    if spec.spans.amplifier.type == "none":
        return 0.0
    if spec.spans.amplifier.mode == "auto_gain":
        max_gain_db = spec.spans.amplifier.max_gain_db or 0.0
        return min(span_loss_db, max_gain_db)
    if spec.spans.amplifier.mode == "fixed_gain":
        return float(spec.spans.amplifier.fixed_gain_db or 0.0)
    return 0.0


def build_tx_params(
    spec: TxSpecSlice, seed: int, format_tag: Literal["coherent", "pam"]
) -> parameters:
    param = parameters()
    param.seed = seed
    param.Rs = spec.signal.symbol_rate_baud
    param.SpS = spec.runtime.samples_per_symbol
    param.pulseRollOff = spec.signal.rolloff
    param.nPolModes = spec.signal.n_pol
    param.prgsBar = False

    if format_tag == "coherent":
        bits_per_symbol_val = int(np.log2(4))
    elif spec.signal.format == "imdd_ook":
        bits_per_symbol_val = int(np.log2(2))
    else:
        bits_per_symbol_val = int(np.log2(4))
    param.nBits = int(spec.runtime.n_symbols * bits_per_symbol_val)

    if format_tag == "coherent":
        param.M = 4
        param.constType = "psk"
        param.nChannels = 1
        param.powerPerChannel = spec.transceiver.tx.launch_power_dbm
        param.laserLinewidth = spec.transceiver.tx.laser_linewidth_hz
        param.Fc = units.carrier_frequency_hz()
        param.wdmGridSpacing = 50e9
        param.pulseType = "rrc"
        param.nFilterTaps = 1024
    else:
        if spec.signal.format == "imdd_ook":
            param.M = 2
        else:
            param.M = 4
        param.power = spec.transceiver.tx.launch_power_dbm
        param.pulseType = "nrz"
        param.nFilterTaps = 256
        param.returnParam = True
    return param


def build_channel_params(spec: ChannelSpecSlice, seed: int) -> tuple[parameters, ChannelLayout]:
    param = parameters()
    layout = _channel_layout(spec)
    param.Ltotal = layout.total_length_km
    param.Lspan = layout.span_length_km
    param.hz = spec.propagation.ssfm.dz_m / 1000.0
    param.alpha = spec.fiber.alpha_db_per_km
    param.gamma = spec.fiber.gamma_w_inv_m * 1e3
    param.Fc = units.carrier_frequency_hz()
    param.Fs = spec.signal.symbol_rate_baud * spec.runtime.samples_per_symbol
    param.prgsBar = False
    param.seed = seed
    param.returnParameters = True

    param.D = _beta2_to_dispersion(spec.fiber.beta2_s2_per_m, param.Fc)

    effects = spec.propagation.effects
    if not effects.dispersion:
        param.D = 0.0
    if not effects.nonlinearity:
        param.gamma = 0.0
    param.pmd_ps_sqrt_km = spec.fiber.pmd_ps_sqrt_km if effects.pmd else 0.0
    param.env_effects = effects.env_effects

    span_loss_db = _span_loss_db(spec, layout)
    param.span_loss_db = span_loss_db
    param.amp_gain_db = _amplifier_gain_db(spec, span_loss_db)
    param.amp_mode = spec.spans.amplifier.mode

    if spec.spans.amplifier.type == "edfa":
        if effects.ase:
            param.amp = "edfa"
            param.NF = spec.spans.amplifier.noise_figure_db or 0.0
        else:
            param.amp = "ideal"
            param.NF = 0.0
    else:
        param.amp = None
        param.NF = 0.0
    return param, layout


def build_lo_params(spec: RxFrontEndSpecSlice, seed: int, n_samples: int) -> parameters:
    param = parameters()
    param.P = spec.transceiver.tx.launch_power_dbm
    param.lw = spec.transceiver.rx.lo_linewidth_hz
    param.Fs = spec.signal.symbol_rate_baud * spec.runtime.samples_per_symbol
    param.Ns = n_samples
    param.seed = seed
    return param


def build_pd_params(spec: RxFrontEndSpecSlice, seed: int) -> parameters:
    param = parameters()
    param.Fs = spec.signal.symbol_rate_baud * spec.runtime.samples_per_symbol
    param.B = spec.signal.symbol_rate_baud / 2
    param.ideal = False
    param.shotNoise = spec.transceiver.rx.noise.shot
    param.thermalNoise = spec.transceiver.rx.noise.thermal
    param.seed = seed
    return param


def build_resample_params(in_fs: float, out_fs: float) -> parameters:
    param = parameters()
    param.inFs = in_fs
    param.outFs = out_fs
    param.N = 501
    return param


def build_edc_params(spec: DspSpecSlice) -> parameters:
    param = parameters()
    param.L = total_link_length_m(spec.path) / 1000.0
    param.D = _beta2_to_dispersion(spec.fiber.beta2_s2_per_m, units.carrier_frequency_hz())
    param.Fc = units.carrier_frequency_hz()
    param.Fs = spec.signal.symbol_rate_baud * spec.runtime.samples_per_symbol
    return param


def build_mimo_eq_params(spec: DspSpecSlice, taps: int, mu: float) -> parameters:
    param = parameters()
    param.nTaps = taps
    param.mu = [mu]
    param.SpS = spec.runtime.samples_per_symbol
    param.alg = ["nlms"]
    param.M = 4
    param.constType = "psk" if spec.signal.format == "coherent_qpsk" else "pam"
    param.prgsBar = False
    return param

from __future__ import annotations

from math import isclose

from fiber_link_sim.data_models.spec_models import SimulationSpec
from fiber_link_sim.data_models.stage_models import MetricsSpecSlice
from fiber_link_sim.latency import compute_latency_budget


def _base_spec(length_m: float) -> dict:
    return {
        "v": "0.2",
        "path": {"segments": [{"length_m": length_m, "temp_c": 20.0}], "geo": {"enabled": False}},
        "fiber": {
            "alpha_db_per_km": 0.2,
            "beta2_s2_per_m": -2.17e-26,
            "beta3_s3_per_m": None,
            "gamma_w_inv_m": 0.0,
            "pmd_ps_sqrt_km": 0.0,
            "n_group": 1.4682,
        },
        "spans": {
            "mode": "fixed_span_length",
            "span_length_m": 80_000.0,
            "amplifier": {
                "type": "edfa",
                "mode": "auto_gain",
                "noise_figure_db": 5.0,
                "max_gain_db": 20.0,
            },
        },
        "signal": {
            "format": "imdd_ook",
            "symbol_rate_baud": 25e9,
            "rolloff": 0.2,
            "n_pol": 1,
            "frame": {"payload_bits": 1024, "preamble_bits": 0, "pilot_bits": 0},
        },
        "transceiver": {
            "tx": {"laser_linewidth_hz": 0.0, "launch_power_dbm": 0.0},
            "rx": {
                "coherent": False,
                "lo_linewidth_hz": 0.0,
                "adc": {"sample_rate_hz": 100e9, "bits": 8},
                "noise": {"thermal": False, "shot": False},
            },
        },
        "processing": {
            "dsp_chain": [],
            "fec": {"enabled": False, "scheme": "none", "code_rate": 1.0, "params": {}},
        },
        "propagation": {
            "model": "scalar_glnse",
            "backend": "builtin_ssfm",
            "effects": {
                "dispersion": False,
                "nonlinearity": False,
                "ase": False,
                "pmd": False,
                "env_effects": False,
            },
            "ssfm": {"dz_m": 1000.0, "step_adapt": False},
        },
        "latency_model": {
            "serialization_weight": 1.0,
            "processing_weight": 0.0,
            "processing_floor_s": 0.0,
        },
        "runtime": {"seed": 7, "n_symbols": 1024, "samples_per_symbol": 2, "max_runtime_s": 5.0},
        "outputs": {"artifact_level": "none", "return_waveforms": False},
    }


def test_hft_route_latency_examples_match_reference_one_way_ms() -> None:
    route_lengths_m = {
        "chicago_nj": 1_300_000.0,
        "london_frankfurt": 700_000.0,
        "new_york_london": 6_500_000.0,
    }

    for length_m in route_lengths_m.values():
        spec = SimulationSpec.model_validate(_base_spec(length_m))
        budget, _ = compute_latency_budget(MetricsSpecSlice.from_spec(spec), {})
        expected_s = length_m * 1.4682 / 299_792_458.0
        assert isclose(budget["propagation_s"], expected_s, rel_tol=0.0, abs_tol=0.0)

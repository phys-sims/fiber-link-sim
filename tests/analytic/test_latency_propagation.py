from __future__ import annotations

from math import isclose

from fiber_link_sim.data_models.spec_models import SimulationSpec
from fiber_link_sim.data_models.stage_models import MetricsSpecSlice
from fiber_link_sim.latency import compute_latency_budget


def test_latency_propagation_matches_group_index() -> None:
    spec = SimulationSpec.model_validate(
        {
            "v": "0.2",
            "path": {
                "segments": [{"length_m": 500.0}, {"length_m": 1500.0}],
                "geo": {"enabled": False},
            },
            "fiber": {
                "alpha_db_per_km": 0.2,
                "beta2_s2_per_m": -2.17e-26,
                "beta3_s3_per_m": None,
                "gamma_w_inv_m": 0.0013,
                "pmd_ps_sqrt_km": 0.0,
                "n_group": 1.9,
            },
            "spans": {
                "mode": "from_path_segments",
                "span_length_m": 1000.0,
                "amplifier": {"type": "none", "mode": "none"},
            },
            "signal": {
                "format": "imdd_ook",
                "symbol_rate_baud": 10.0,
                "rolloff": 0.2,
                "n_pol": 1,
                "frame": {"payload_bits": 100, "preamble_bits": 0, "pilot_bits": 0},
            },
            "transceiver": {
                "tx": {"laser_linewidth_hz": 0.0, "launch_power_dbm": 0.0},
                "rx": {
                    "coherent": False,
                    "lo_linewidth_hz": 0.0,
                    "adc": {"sample_rate_hz": 40.0, "bits": 8},
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
                "ssfm": {"dz_m": 100.0, "step_adapt": False},
            },
            "latency_model": {
                "serialization_weight": 1.0,
                "processing_weight": 0.0,
                "processing_floor_s": 0.0,
            },
            "runtime": {
                "seed": 0,
                "n_symbols": 128,
                "samples_per_symbol": 2,
                "max_runtime_s": 10.0,
            },
            "outputs": {"artifact_level": "none", "return_waveforms": False},
        }
    )
    budget, _ = compute_latency_budget(MetricsSpecSlice.from_spec(spec), {})
    expected = (500.0 + 1500.0) * 1.9 / 299_792_458.0
    assert isclose(budget["propagation_s"], expected, rel_tol=0.0, abs_tol=0.0)

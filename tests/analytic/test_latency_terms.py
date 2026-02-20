from __future__ import annotations

from math import isclose

from fiber_link_sim.data_models.spec_models import SimulationSpec
from fiber_link_sim.data_models.stage_models import MetricsSpecSlice
from fiber_link_sim.latency import compute_latency_budget


def _base_spec() -> dict:
    return {
        "v": "0.3",
        "path": {"segments": [{"length_m": 1000.0}], "geo": {"enabled": False}},
        "fiber": {
            "alpha_db_per_km": 0.2,
            "beta2_s2_per_m": -2.17e-26,
            "beta3_s3_per_m": None,
            "gamma_w_inv_m": 0.0,
            "pmd_ps_sqrt_km": 0.0,
            "n_group": 2.0,
        },
        "spans": {
            "mode": "from_path_segments",
            "span_length_m": 1000.0,
            "amplifier": {"type": "none", "mode": "none"},
        },
        "signal": {
            "format": "imdd_ook",
            "symbol_rate_baud": 20.0,
            "rolloff": 0.2,
            "n_pol": 1,
            "frame": {"payload_bits": 200, "preamble_bits": 20, "pilot_bits": 10},
        },
        "transceiver": {
            "tx": {"laser_linewidth_hz": 0.0, "launch_power_dbm": 0.0},
            "rx": {
                "coherent": False,
                "lo_linewidth_hz": 0.0,
                "adc": {"sample_rate_hz": 100.0, "bits": 8},
            },
        },
        "processing": {
            "dsp_chain": [],
            "fec": {
                "enabled": True,
                "scheme": "ldpc",
                "code_rate": 0.8,
                "params": {"block_size_bits": 100},
            },
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
            "framing": {
                "include_preamble_bits": False,
                "include_pilot_bits": False,
                "fec_overhead_mode": "none",
            },
            "queueing": {
                "ingress_buffer_s": 0.0,
                "egress_buffer_s": 0.0,
                "scheduler_tick_s": 0.0,
            },
            "hardware_pipeline": {
                "tx_fixed_s": 0.0,
                "rx_fixed_s": 0.0,
                "dsp_fixed_s": 0.0,
                "fec_fixed_s": 0.0,
            },
        },
        "runtime": {"seed": 1, "n_symbols": 128, "samples_per_symbol": 2, "max_runtime_s": 1.0},
        "outputs": {"artifact_level": "none", "return_waveforms": False},
    }


def test_queueing_term_isolated() -> None:
    spec_dict = _base_spec()
    spec_dict["latency_model"]["queueing"] = {
        "ingress_buffer_s": 0.01,
        "egress_buffer_s": 0.02,
        "scheduler_tick_s": 0.03,
    }
    spec = SimulationSpec.model_validate(spec_dict)
    budget, _ = compute_latency_budget(MetricsSpecSlice.from_spec(spec), {})
    assert isclose(budget["queueing_s"], 0.06, rel_tol=0.0, abs_tol=0.0)


def test_framing_overhead_term_isolated() -> None:
    spec_dict = _base_spec()
    spec_dict["latency_model"]["framing"] = {
        "include_preamble_bits": True,
        "include_pilot_bits": True,
        "fec_overhead_mode": "fixed_ratio",
        "fec_overhead_ratio": 0.25,
    }
    spec_dict["latency_model"]["serialization_weight"] = 2.0
    spec = SimulationSpec.model_validate(spec_dict)
    budget, _ = compute_latency_budget(MetricsSpecSlice.from_spec(spec), {})
    expected = (20 + 10 + 50) / 20.0 * 2.0
    assert isclose(budget["framing_overhead_s"], expected, rel_tol=0.0, abs_tol=0.0)


def test_hardware_pipeline_term_isolated() -> None:
    spec_dict = _base_spec()
    spec_dict["latency_model"]["hardware_pipeline"] = {
        "tx_fixed_s": 0.1,
        "rx_fixed_s": 0.2,
        "dsp_fixed_s": 0.3,
        "fec_fixed_s": 0.4,
    }
    spec = SimulationSpec.model_validate(spec_dict)
    budget, _ = compute_latency_budget(MetricsSpecSlice.from_spec(spec), {})
    assert isclose(budget["hardware_pipeline_s"], 1.0, rel_tol=0.0, abs_tol=0.0)

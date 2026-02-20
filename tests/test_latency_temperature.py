from __future__ import annotations

from math import isclose
from typing import Any

from fiber_link_sim.data_models.spec_models import SimulationSpec
from fiber_link_sim.data_models.stage_models import MetricsSpecSlice
from fiber_link_sim.latency import compute_latency_budget


def _temperature_spec(
    temp_c: float,
    *,
    env_effects: bool = True,
    seed: int = 11,
    group_delay_temp_coeff_per_c: float = 7e-6,
    sigma_c: float = 1.0,
    sampling_policy: str = "normal_mc",
) -> SimulationSpec:
    return SimulationSpec.model_validate(
        {
            "v": "0.3",
            "path": {
                "segments": [{"length_m": 100_000.0, "temp_c": temp_c}],
                "geo": {"enabled": False},
            },
            "fiber": {
                "alpha_db_per_km": 0.2,
                "beta2_s2_per_m": -2.17e-26,
                "beta3_s3_per_m": None,
                "gamma_w_inv_m": 0.0,
                "pmd_ps_sqrt_km": 0.0,
                "n_group": 1.4682,
            },
            "spans": {
                "mode": "from_path_segments",
                "span_length_m": 100_000.0,
                "amplifier": {"type": "none", "mode": "none"},
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
                    "env_effects": env_effects,
                },
                "ssfm": {"dz_m": 1_000.0, "step_adapt": False},
            },
            "latency_model": {
                "serialization_weight": 1.0,
                "processing_weight": 0.0,
                "processing_floor_s": 0.0,
                "environment": {
                    "version": "v1",
                    "group_delay_temp_coeff_per_c": group_delay_temp_coeff_per_c,
                    "spread": {
                        "sigma_c": sigma_c,
                        "samples": 512,
                        "sampling_policy": sampling_policy,
                    },
                },
            },
            "runtime": {
                "seed": seed,
                "n_symbols": 1024,
                "samples_per_symbol": 2,
                "max_runtime_s": 10.0,
            },
            "outputs": {"artifact_level": "none", "return_waveforms": False},
        }
    )


def _spread(meta: dict[str, Any]) -> dict[str, float]:
    return meta["inputs_used"]["propagation_spread_s"]


def test_temperature_increases_propagation_when_env_effects_enabled() -> None:
    cool = _temperature_spec(5.0)
    hot = _temperature_spec(35.0)

    cool_budget, cool_meta = compute_latency_budget(MetricsSpecSlice.from_spec(cool), {})
    hot_budget, _ = compute_latency_budget(MetricsSpecSlice.from_spec(hot), {})

    assert hot_budget["propagation_s"] > cool_budget["propagation_s"]
    assert "environment.group_delay_temp_coeff_per_c" in cool_meta["inputs_used"]
    assert "environment.spread.sigma_c" in cool_meta["inputs_used"]
    assert "propagation_spread_s" in cool_meta["inputs_used"]


def test_temperature_spread_is_deterministic_for_same_seed() -> None:
    spec_a = _temperature_spec(20.0, seed=99)
    spec_b = _temperature_spec(20.0, seed=99)

    _, meta_a = compute_latency_budget(MetricsSpecSlice.from_spec(spec_a), {})
    _, meta_b = compute_latency_budget(MetricsSpecSlice.from_spec(spec_b), {})

    spread_a = _spread(meta_a)
    spread_b = _spread(meta_b)
    assert spread_a == spread_b
    assert spread_a["p95_s"] > spread_a["p05_s"]


def test_spread_sigma_sensitivity_affects_std() -> None:
    low_sigma_spec = _temperature_spec(20.0, sigma_c=0.2, seed=7)
    high_sigma_spec = _temperature_spec(20.0, sigma_c=4.0, seed=7)

    _, low_meta = compute_latency_budget(MetricsSpecSlice.from_spec(low_sigma_spec), {})
    _, high_meta = compute_latency_budget(MetricsSpecSlice.from_spec(high_sigma_spec), {})

    assert _spread(high_meta)["std_s"] > _spread(low_meta)["std_s"]


def test_temp_coefficient_sensitivity_affects_spread() -> None:
    low_coeff_spec = _temperature_spec(20.0, group_delay_temp_coeff_per_c=2e-6, seed=13)
    high_coeff_spec = _temperature_spec(20.0, group_delay_temp_coeff_per_c=1.2e-5, seed=13)

    _, low_meta = compute_latency_budget(MetricsSpecSlice.from_spec(low_coeff_spec), {})
    _, high_meta = compute_latency_budget(MetricsSpecSlice.from_spec(high_coeff_spec), {})

    assert _spread(high_meta)["std_s"] > _spread(low_meta)["std_s"]


def test_temperature_ignored_when_env_effects_disabled() -> None:
    cool = _temperature_spec(0.0, env_effects=False)
    hot = _temperature_spec(40.0, env_effects=False)

    cool_budget, _ = compute_latency_budget(MetricsSpecSlice.from_spec(cool), {})
    hot_budget, _ = compute_latency_budget(MetricsSpecSlice.from_spec(hot), {})

    assert isclose(
        cool_budget["propagation_s"], hot_budget["propagation_s"], rel_tol=0.0, abs_tol=0.0
    )

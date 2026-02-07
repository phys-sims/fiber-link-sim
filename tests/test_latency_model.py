from __future__ import annotations

from math import isclose

from fiber_link_sim.data_models.spec_models import SimulationSpec
from fiber_link_sim.stages.core import MetricsStage
from fiber_link_sim.stages.base import SimulationState
from fiber_link_sim.stages.configs import MetricsStageConfig


def test_latency_model_breakdown_exact() -> None:
    spec = SimulationSpec.model_validate(
        {
            "v": "0.2",
            "path": {"segments": [{"length_m": 1000.0}], "geo": {"enabled": False}},
            "fiber": {
                "alpha_db_per_km": 0.2,
                "beta2_s2_per_m": -2.17e-26,
                "beta3_s3_per_m": None,
                "gamma_w_inv_m": 0.0013,
                "pmd_ps_sqrt_km": 0.0,
                "n_group": 2.0,
            },
            "spans": {
                "mode": "from_path_segments",
                "span_length_m": 1000.0,
                "amplifier": {"type": "none", "mode": "none"},
            },
            "signal": {
                "format": "coherent_qpsk",
                "symbol_rate_baud": 10.0,
                "rolloff": 0.2,
                "n_pol": 2,
                "frame": {"payload_bits": 100, "preamble_bits": 0, "pilot_bits": 0},
            },
            "transceiver": {
                "tx": {"laser_linewidth_hz": 0.0, "launch_power_dbm": 0.0},
                "rx": {
                    "coherent": True,
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
                "model": "manakov",
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
                "serialization_weight": 1.25,
                "processing_weight": 0.5,
                "processing_floor_s": 0.1,
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
    state = SimulationState()
    state.optical["total_length_m"] = 1000.0
    state.tx["total_bits"] = 80
    state.stats["bits_per_symbol"] = 2
    state.stats["pre_fec_ber"] = 0.0
    state.stats["snr_db"] = 0.0
    state.stats["evm_rms"] = 0.0

    stage = MetricsStage(cfg=MetricsStageConfig(spec=spec))
    result = stage.process(state)
    latency = result.state.stats["summary"]["latency_s"]

    c_m_s = 299_792_458.0
    propagation_expected = 1000.0 / (c_m_s / 2.0)
    serialization_expected = 80 / (10.0 * 2) * 1.25
    processing_expected = max(0.1, 128 / 10.0 * 0.5)
    total_expected = propagation_expected + serialization_expected + processing_expected

    assert isclose(latency["propagation"], propagation_expected, rel_tol=0.0, abs_tol=0.0)
    assert isclose(latency["serialization"], serialization_expected, rel_tol=0.0, abs_tol=0.0)
    assert isclose(latency["processing_est"], processing_expected, rel_tol=0.0, abs_tol=0.0)
    assert isclose(latency["total"], total_expected, rel_tol=0.0, abs_tol=0.0)

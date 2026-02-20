from __future__ import annotations

from math import isclose

from fiber_link_sim.data_models.spec_models import SimulationSpec
from fiber_link_sim.data_models.stage_models import MetricsSpecSlice
from fiber_link_sim.stages.base import SimulationState
from fiber_link_sim.stages.configs import MetricsStageConfig
from fiber_link_sim.stages.core import MetricsStage


def test_latency_model_breakdown_exact() -> None:
    spec = SimulationSpec.model_validate(
        {
            "v": "0.3",
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
                "frame": {"payload_bits": 100, "preamble_bits": 16, "pilot_bits": 8},
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
                "dsp_chain": [{"name": "matched_filter", "enabled": False, "params": {}}],
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
                "queueing": {
                    "ingress_buffer_s": 0.01,
                    "egress_buffer_s": 0.02,
                    "scheduler_tick_s": 0.03,
                },
                "framing": {
                    "include_preamble_bits": True,
                    "include_pilot_bits": True,
                    "fec_overhead_mode": "fixed_ratio",
                    "fec_overhead_ratio": 0.1,
                },
                "hardware_pipeline": {
                    "tx_fixed_s": 0.04,
                    "rx_fixed_s": 0.05,
                    "dsp_fixed_s": 0.06,
                    "fec_fixed_s": 0.07,
                },
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
    state.stats["total_length_m"] = 1000.0
    state.stats["total_bits"] = 80
    state.stats["bits_per_symbol"] = 2
    state.stats["pre_fec_ber"] = 0.0
    state.stats["snr_db"] = 0.0
    state.stats["evm_rms"] = 0.0

    stage = MetricsStage(
        cfg=MetricsStageConfig(name="metrics", spec=MetricsSpecSlice.from_spec(spec))
    )
    result = stage.process(state)
    latency = result.state.stats["summary"]["latency_s"]

    c_m_s = 299_792_458.0
    propagation_expected = 1000.0 * 2.0 / c_m_s
    serialization_expected = 100 / (10.0 * 2 * 2) * 1.25
    framing_overhead_expected = (16 + 8 + 10) / (10.0 * 2 * 2) * 1.25
    processing_expected = max(0.1, 128 / 10.0 * 0.5)
    queueing_expected = 0.01 + 0.02 + 0.03
    hardware_expected = 0.04 + 0.05 + 0.06 + 0.07
    total_expected = (
        propagation_expected
        + serialization_expected
        + framing_overhead_expected
        + hardware_expected
        + queueing_expected
        + processing_expected
    )

    assert isclose(latency["propagation_s"], propagation_expected, rel_tol=0.0, abs_tol=0.0)
    assert isclose(latency["serialization_s"], serialization_expected, rel_tol=0.0, abs_tol=0.0)
    assert isclose(
        latency["framing_overhead_s"], framing_overhead_expected, rel_tol=0.0, abs_tol=0.0
    )
    assert isclose(latency["dsp_group_delay_s"], 0.0, rel_tol=0.0, abs_tol=0.0)
    assert isclose(latency["fec_block_s"], 0.0, rel_tol=0.0, abs_tol=0.0)
    assert isclose(latency["hardware_pipeline_s"], hardware_expected, rel_tol=0.0, abs_tol=0.0)
    assert isclose(latency["queueing_s"], queueing_expected, rel_tol=0.0, abs_tol=0.0)
    assert isclose(latency["processing_s"], processing_expected, rel_tol=0.0, abs_tol=0.0)
    assert isclose(latency["total_s"], total_expected, rel_tol=0.0, abs_tol=0.0)


def test_latency_defaults_reported_when_new_terms_omitted() -> None:
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
                "format": "imdd_ook",
                "symbol_rate_baud": 10.0,
                "rolloff": 0.2,
                "n_pol": 1,
                "frame": {"payload_bits": 100, "preamble_bits": 5, "pilot_bits": 3},
            },
            "transceiver": {
                "tx": {"laser_linewidth_hz": 0.0, "launch_power_dbm": 0.0},
                "rx": {
                    "coherent": False,
                    "lo_linewidth_hz": 0.0,
                    "adc": {"sample_rate_hz": 40.0, "bits": 8},
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
    stage = MetricsStage(
        cfg=MetricsStageConfig(name="metrics", spec=MetricsSpecSlice.from_spec(spec))
    )
    state = SimulationState()
    state.stats["pre_fec_ber"] = 0.0
    state.stats["post_fec_ber"] = 0.0
    state.stats["fer"] = 0.0
    state.stats["evm_rms"] = 1.0
    result = stage.process(state)
    metadata = result.state.stats["summary"]["latency_metadata"]

    assert metadata["schema_version"] == "v0.3"
    defaults = metadata["defaults_used"]
    assert defaults["queueing.ingress_buffer_s"] == 0.0
    assert defaults["queueing.egress_buffer_s"] == 0.0
    assert defaults["queueing.scheduler_tick_s"] == 0.0
    assert defaults["hardware_pipeline.tx_fixed_s"] == 0.0
    assert defaults["hardware_pipeline.rx_fixed_s"] == 0.0
    assert defaults["hardware_pipeline.dsp_fixed_s"] == 0.0
    assert defaults["hardware_pipeline.fec_fixed_s"] == 0.0
    assert defaults["framing.include_preamble_bits"] is False
    assert defaults["framing.include_pilot_bits"] is False
    assert defaults["framing.fec_overhead_mode"] == "none"
    assert defaults["framing.fec_overhead_ratio"] is None

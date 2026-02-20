from __future__ import annotations

from typing import Any

import numpy as np

from fiber_link_sim.adapters.opticommpy.dsp import resolve_dsp_chain
from fiber_link_sim.data_models.spec_models import Signal
from fiber_link_sim.data_models.stage_models import DspSpecSlice, MetricsSpecSlice
from fiber_link_sim.utils import bits_per_symbol, total_link_length_m

_C_M_S = 299_792_458.0


def compute_latency_budget(
    spec: MetricsSpecSlice, stats: dict[str, Any]
) -> tuple[dict[str, float], dict[str, Any]]:
    assumptions: list[str] = []
    defaults_used: dict[str, Any] = {}
    inputs_used: dict[str, Any] = {}

    total_length_m = float(stats.get("total_length_m") or total_link_length_m(spec.path))
    inputs_used["path_length_m"] = total_length_m
    inputs_used["fiber_n_group"] = spec.fiber.n_group
    env_inputs, env_defaults = _environment_inputs(spec)
    inputs_used.update(env_inputs)
    defaults_used.update(env_defaults)
    propagation_s, propagation_inputs, propagation_defaults, propagation_assumptions = (
        _propagation_latency(spec)
    )
    inputs_used.update(propagation_inputs)
    defaults_used.update(propagation_defaults)
    assumptions.extend(propagation_assumptions)

    spread = _propagation_spread_estimate(spec)
    if spread is not None:
        inputs_used["propagation_spread_s"] = spread

    bits_per_sym = bits_per_symbol(spec.signal)
    payload_bits = int(spec.signal.frame.payload_bits)
    framing_bits, framing_defaults, framing_inputs, framing_assumptions = _framing_bits(spec)
    defaults_used.update(framing_defaults)
    inputs_used.update(framing_inputs)
    assumptions.extend(framing_assumptions)

    inputs_used["payload_bits"] = payload_bits
    inputs_used["symbol_rate_baud"] = spec.signal.symbol_rate_baud
    inputs_used["bits_per_symbol"] = bits_per_sym

    serialization_s = (
        payload_bits
        / (spec.signal.symbol_rate_baud * bits_per_sym)
        * spec.latency_model.serialization_weight
    )
    framing_overhead_s = (
        framing_bits
        / (spec.signal.symbol_rate_baud * bits_per_sym)
        * spec.latency_model.serialization_weight
    )

    dsp_group_delay_s, dsp_defaults, dsp_inputs, dsp_assumptions = _dsp_group_delay(spec)
    defaults_used.update(dsp_defaults)
    inputs_used.update(dsp_inputs)
    assumptions.extend(dsp_assumptions)

    processing_s = max(
        spec.latency_model.processing_floor_s,
        spec.runtime.n_symbols
        / spec.signal.symbol_rate_baud
        * spec.latency_model.processing_weight,
    )
    inputs_used["processing_floor_s"] = spec.latency_model.processing_floor_s
    inputs_used["processing_weight"] = spec.latency_model.processing_weight
    inputs_used["runtime_n_symbols"] = spec.runtime.n_symbols

    fec_block_s, fec_defaults, fec_inputs, fec_assumptions = _fec_block_latency(spec)
    defaults_used.update(fec_defaults)
    inputs_used.update(fec_inputs)
    assumptions.extend(fec_assumptions)

    queueing_s, queue_defaults, queue_inputs, queue_assumptions = _queueing_latency(spec)
    defaults_used.update(queue_defaults)
    inputs_used.update(queue_inputs)
    assumptions.extend(queue_assumptions)

    hardware_pipeline_s, hw_defaults, hw_inputs, hw_assumptions = _hardware_pipeline_latency(spec)
    defaults_used.update(hw_defaults)
    inputs_used.update(hw_inputs)
    assumptions.extend(hw_assumptions)

    total_s = (
        propagation_s
        + serialization_s
        + framing_overhead_s
        + dsp_group_delay_s
        + fec_block_s
        + hardware_pipeline_s
        + queueing_s
        + processing_s
    )

    budget = {
        "propagation_s": propagation_s,
        "serialization_s": serialization_s,
        "framing_overhead_s": framing_overhead_s,
        "dsp_group_delay_s": dsp_group_delay_s,
        "fec_block_s": fec_block_s,
        "hardware_pipeline_s": hardware_pipeline_s,
        "queueing_s": queueing_s,
        "processing_s": processing_s,
        "total_s": total_s,
    }
    metadata = {
        "assumptions": assumptions,
        "inputs_used": inputs_used,
        "defaults_used": defaults_used,
        "schema_version": "v0.3",
    }
    return budget, metadata


def _queueing_latency(
    spec: MetricsSpecSlice,
) -> tuple[float, dict[str, Any], dict[str, Any], list[str]]:
    assumptions: list[str] = []
    defaults_used: dict[str, Any] = {}
    inputs_used: dict[str, Any] = {}

    queueing_model = spec.latency_model.queueing
    total_s = (
        queueing_model.ingress_buffer_s
        + queueing_model.egress_buffer_s
        + queueing_model.scheduler_tick_s
    )

    queue_fields = queueing_model.model_fields_set
    for field_name in ("ingress_buffer_s", "egress_buffer_s", "scheduler_tick_s"):
        value = float(getattr(queueing_model, field_name))
        inputs_used[f"queueing.{field_name}"] = value
        if field_name not in queue_fields:
            defaults_used[f"queueing.{field_name}"] = value

    assumptions.append("Queueing latency is ingress + egress buffering + scheduler tick.")
    return total_s, defaults_used, inputs_used, assumptions


def _hardware_pipeline_latency(
    spec: MetricsSpecSlice,
) -> tuple[float, dict[str, Any], dict[str, Any], list[str]]:
    assumptions: list[str] = ["Hardware pipeline latency sums fixed TX/RX/DSP/FEC delays."]
    defaults_used: dict[str, Any] = {}
    inputs_used: dict[str, Any] = {}

    hw = spec.latency_model.hardware_pipeline
    total_s = hw.tx_fixed_s + hw.rx_fixed_s + hw.dsp_fixed_s + hw.fec_fixed_s
    hw_fields = hw.model_fields_set
    for field_name in ("tx_fixed_s", "rx_fixed_s", "dsp_fixed_s", "fec_fixed_s"):
        value = float(getattr(hw, field_name))
        inputs_used[f"hardware_pipeline.{field_name}"] = value
        if field_name not in hw_fields:
            defaults_used[f"hardware_pipeline.{field_name}"] = value

    return total_s, defaults_used, inputs_used, assumptions


def _framing_bits(
    spec: MetricsSpecSlice,
) -> tuple[int, dict[str, Any], dict[str, Any], list[str]]:
    assumptions: list[str] = []
    defaults_used: dict[str, Any] = {}
    inputs_used: dict[str, Any] = {}

    framing = spec.latency_model.framing
    framing_fields = framing.model_fields_set

    preamble_bits = int(spec.signal.frame.preamble_bits) if framing.include_preamble_bits else 0
    pilot_bits = int(spec.signal.frame.pilot_bits) if framing.include_pilot_bits else 0
    if not framing.include_preamble_bits and spec.signal.frame.preamble_bits:
        assumptions.append("Framing preamble bits excluded from latency by configuration.")
    if not framing.include_pilot_bits and spec.signal.frame.pilot_bits:
        assumptions.append("Framing pilot bits excluded from latency by configuration.")

    overhead_bits = 0.0
    fec_mode = framing.fec_overhead_mode
    if fec_mode == "auto_from_code_rate":
        code_rate = float(spec.processing.fec.code_rate)
        if code_rate <= 0:
            assumptions.append(
                "FEC code rate non-positive; automatic framing overhead set to 0 bits."
            )
        else:
            overhead_bits = int(round(spec.signal.frame.payload_bits * ((1.0 / code_rate) - 1.0)))
        inputs_used["framing.fec_auto_code_rate"] = code_rate
    elif fec_mode == "fixed_ratio":
        ratio = float(framing.fec_overhead_ratio or 0.0)
        overhead_bits = int(round(spec.signal.frame.payload_bits * ratio))
        inputs_used["framing.fec_overhead_ratio"] = ratio

    for field_name in (
        "include_preamble_bits",
        "include_pilot_bits",
        "fec_overhead_mode",
        "fec_overhead_ratio",
    ):
        if field_name not in framing_fields:
            defaults_used[f"framing.{field_name}"] = getattr(framing, field_name)

    inputs_used["framing.preamble_bits_counted"] = preamble_bits
    inputs_used["framing.pilot_bits_counted"] = pilot_bits
    inputs_used["framing.fec_overhead_bits"] = int(overhead_bits)

    total_framing_bits = int(preamble_bits + pilot_bits + overhead_bits)
    assumptions.append("Framing overhead latency is converted from counted framing bits.")
    return total_framing_bits, defaults_used, inputs_used, assumptions


def _propagation_latency(
    spec: MetricsSpecSlice,
) -> tuple[float, dict[str, Any], dict[str, Any], list[str]]:
    inputs_used: dict[str, Any] = {}
    defaults_used: dict[str, Any] = {}
    assumptions: list[str] = []

    if not spec.propagation.effects.env_effects:
        assumptions.append(
            "Propagation latency uses constant fiber.n_group (env_effects disabled)."
        )
        return (
            total_link_length_m(spec.path) * spec.fiber.n_group / _C_M_S,
            inputs_used,
            defaults_used,
            assumptions,
        )

    assumptions.append(
        "Temperature-aware propagation uses per-segment temp_c and "
        "a linear group-delay coefficient."
    )

    env = spec.latency_model.environment

    delay_s = 0.0
    for segment in spec.path.segments:
        segment_temp_c = (
            env.temperature_reference_c if segment.temp_c is None else float(segment.temp_c)
        )
        n_eff = spec.fiber.n_group * (
            1.0 + env.group_delay_temp_coeff_per_c * (segment_temp_c - env.temperature_reference_c)
        )
        delay_s += float(segment.length_m) * n_eff / _C_M_S

    return delay_s, inputs_used, defaults_used, assumptions


def _propagation_spread_estimate(spec: MetricsSpecSlice) -> dict[str, float] | None:
    if not spec.propagation.effects.env_effects:
        return None

    if not spec.path.segments:
        return None

    env = spec.latency_model.environment
    if env.spread.sampling_policy != "normal_mc":
        return None

    rng = np.random.default_rng(spec.runtime.seed + 17)
    temps_c = np.array(
        [
            env.temperature_reference_c if segment.temp_c is None else float(segment.temp_c)
            for segment in spec.path.segments
        ],
        dtype=float,
    )
    lengths_m = np.array([float(segment.length_m) for segment in spec.path.segments], dtype=float)

    jittered_temps = rng.normal(
        loc=temps_c,
        scale=env.spread.sigma_c,
        size=(env.spread.samples, len(spec.path.segments)),
    )
    n_eff = spec.fiber.n_group * (
        1.0 + env.group_delay_temp_coeff_per_c * (jittered_temps - env.temperature_reference_c)
    )
    delays_s = (lengths_m * n_eff / _C_M_S).sum(axis=1)
    return {
        "p05_s": float(np.percentile(delays_s, 5)),
        "p50_s": float(np.percentile(delays_s, 50)),
        "p95_s": float(np.percentile(delays_s, 95)),
        "std_s": float(np.std(delays_s)),
    }


def _environment_inputs(spec: MetricsSpecSlice) -> tuple[dict[str, Any], dict[str, Any]]:
    env = spec.latency_model.environment
    env_fields = spec.latency_model.model_fields_set
    spread_fields = env.spread.model_fields_set

    inputs_used = {
        "environment.version": env.version,
        "environment.temperature_reference_c": float(env.temperature_reference_c),
        "environment.group_delay_temp_coeff_per_c": float(env.group_delay_temp_coeff_per_c),
        "environment.spread.sigma_c": float(env.spread.sigma_c),
        "environment.spread.samples": int(env.spread.samples),
        "environment.spread.sampling_policy": env.spread.sampling_policy,
    }
    defaults_used: dict[str, Any] = {}

    if "environment" not in env_fields:
        defaults_used["environment"] = "default"
    if "temperature_reference_c" not in env.model_fields_set:
        defaults_used["environment.temperature_reference_c"] = float(env.temperature_reference_c)
    if "group_delay_temp_coeff_per_c" not in env.model_fields_set:
        defaults_used["environment.group_delay_temp_coeff_per_c"] = float(
            env.group_delay_temp_coeff_per_c
        )
    if "spread" not in env.model_fields_set:
        defaults_used["environment.spread"] = "default"
    if "sigma_c" not in spread_fields:
        defaults_used["environment.spread.sigma_c"] = float(env.spread.sigma_c)
    if "samples" not in spread_fields:
        defaults_used["environment.spread.samples"] = int(env.spread.samples)
    if "sampling_policy" not in spread_fields:
        defaults_used["environment.spread.sampling_policy"] = env.spread.sampling_policy

    return inputs_used, defaults_used


def _dsp_group_delay(
    spec: MetricsSpecSlice,
) -> tuple[float, dict[str, Any], dict[str, Any], list[str]]:
    assumptions: list[str] = ["DSP group delay assumes linear-phase FIR (taps/2)."]
    defaults_used: dict[str, Any] = {}
    inputs_used: dict[str, Any] = {}
    group_delay_s = 0.0

    dsp_spec = DspSpecSlice(
        processing=spec.processing,
        signal=spec.signal,
        runtime=spec.runtime,
        fiber=spec.fiber,
        path=spec.path,
    )
    chain = resolve_dsp_chain(dsp_spec, list(spec.processing.dsp_chain))
    inputs_used["dsp_chain"] = [block.name for block in chain if block.enabled]

    current_fs = spec.transceiver.rx.adc.sample_rate_hz
    for block in chain:
        if not block.enabled:
            continue
        if block.name == "resample":
            out_fs = float(block.params.get("out_fs_hz", current_fs))
            if "out_fs_hz" not in block.params:
                defaults_used["dsp.resample.out_fs_hz"] = out_fs
            current_fs = out_fs
            continue
        if block.name == "matched_filter":
            n_taps = int(6 * spec.runtime.samples_per_symbol + 1)
            inputs_used["dsp.matched_filter.n_taps"] = n_taps
            group_delay_s += (n_taps - 1) / 2.0 / current_fs
            continue
        if block.name in {"mimo_eq", "ffe"}:
            taps_default = 15 if block.name == "mimo_eq" else 11
            taps = int(block.params.get("taps", taps_default))
            if "taps" not in block.params:
                defaults_used[f"dsp.{block.name}.taps"] = taps
            inputs_used[f"dsp.{block.name}.taps"] = taps
            group_delay_s += taps / 2.0 / current_fs
            continue
        if block.name == "cd_comp":
            assumptions.append("CD compensation group delay treated as 0 (no FIR tap count).")
            continue

    return group_delay_s, defaults_used, inputs_used, assumptions


def _fec_block_latency(
    spec: MetricsSpecSlice,
) -> tuple[float, dict[str, Any], dict[str, Any], list[str]]:
    assumptions: list[str] = []
    defaults_used: dict[str, Any] = {}
    inputs_used: dict[str, Any] = {}

    if not spec.processing.fec.enabled:
        return 0.0, defaults_used, inputs_used, assumptions

    block_size_bits = _resolve_fec_block_bits(spec.processing.fec.params, spec.signal)
    if "block_size_bits" not in spec.processing.fec.params:
        defaults_used["fec.block_size_bits"] = block_size_bits
    inputs_used["fec.block_size_bits"] = block_size_bits

    raw_line_rate = spec.signal.symbol_rate_baud * bits_per_symbol(spec.signal)
    net_bit_rate = raw_line_rate * spec.processing.fec.code_rate
    inputs_used["fec.code_rate"] = spec.processing.fec.code_rate
    inputs_used["fec.net_bit_rate"] = net_bit_rate
    if net_bit_rate <= 0:
        assumptions.append("FEC net bit rate non-positive; fec_block_s set to 0.0.")
        return 0.0, defaults_used, inputs_used, assumptions

    return block_size_bits / net_bit_rate, defaults_used, inputs_used, assumptions


def _resolve_fec_block_bits(params: dict[str, Any], signal: Signal) -> int:
    if "block_size_bits" in params:
        return int(params["block_size_bits"])
    return int(signal.frame.payload_bits)

from __future__ import annotations

from typing import Any

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
    propagation_s = total_length_m * spec.fiber.n_group / _C_M_S

    payload_bits = int(spec.signal.frame.payload_bits)
    inputs_used["payload_bits"] = payload_bits
    inputs_used["symbol_rate_baud"] = spec.signal.symbol_rate_baud
    inputs_used["bits_per_symbol"] = bits_per_symbol(spec.signal)
    if spec.signal.frame.preamble_bits or spec.signal.frame.pilot_bits:
        assumptions.append(
            "Serialization latency uses payload_bits only; framing overhead ignored."
        )
    serialization_s = (
        payload_bits
        / (spec.signal.symbol_rate_baud * bits_per_symbol(spec.signal))
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

    queueing_s = 0.0
    defaults_used["queueing_s"] = queueing_s
    assumptions.append("Queueing latency set to 0.0 (no buffering model).")

    total_s = (
        propagation_s
        + serialization_s
        + dsp_group_delay_s
        + fec_block_s
        + queueing_s
        + processing_s
    )

    budget = {
        "propagation_s": propagation_s,
        "serialization_s": serialization_s,
        "dsp_group_delay_s": dsp_group_delay_s,
        "fec_block_s": fec_block_s,
        "queueing_s": queueing_s,
        "processing_s": processing_s,
        "total_s": total_s,
    }
    metadata = {
        "assumptions": assumptions,
        "inputs_used": inputs_used,
        "defaults_used": defaults_used,
        "schema_version": "v0.2",
    }
    return budget, metadata


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

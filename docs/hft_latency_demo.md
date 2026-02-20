# HFT Latency Demo Guide

This guide provides a simple, repeatable demo for wrapper-platform users.

## Goals covered

1. Latency model validation against representative HFT routes.
2. Temperature-dependent propagation latency.
3. A deterministic statistical spread estimate for propagation latency.
4. A simple CLI demo path.
5. Runtime benchmarks for optimization planning.

## Route examples included

Three example specs are included under `src/fiber_link_sim/schema/examples/`:

- `hft_chicago_new_jersey.json`
- `hft_london_frankfurt.json`
- `hft_new_york_london.json`

These are representative demo routes (not legal/contract path guarantees).

## CLI demo

Run a route simulation and print result JSON:

```bash
python -m fiber_link_sim.cli src/fiber_link_sim/schema/examples/hft_chicago_new_jersey.json
```

Write result to file:

```bash
python -m fiber_link_sim.cli \
  src/fiber_link_sim/schema/examples/hft_chicago_new_jersey.json \
  --output /tmp/hft_result.json
```

Inspect latency fields in the output:

- `summary.latency_s.propagation_s`
- `summary.latency_s.total_s`
- `summary.latency_metadata.inputs_used.propagation_spread_s`


## Latency formulas and assumptions

The latency budget now uses explicit modeled terms:

- `serialization_s = payload_bits / (symbol_rate_baud * bits_per_symbol) * serialization_weight`
- `framing_overhead_s = framing_bits / (symbol_rate_baud * bits_per_symbol) * serialization_weight`
- `queueing_s = ingress_buffer_s + egress_buffer_s + scheduler_tick_s`
- `hardware_pipeline_s = tx_fixed_s + rx_fixed_s + dsp_fixed_s + fec_fixed_s`

Where framing bits are:

- `preamble_bits` if `latency_model.framing.include_preamble_bits=true`
- `pilot_bits` if `latency_model.framing.include_pilot_bits=true`
- FEC overhead bits from either:
  - `auto_from_code_rate`: `payload_bits * (1/code_rate - 1)`
  - `fixed_ratio`: `payload_bits * fec_overhead_ratio`

All omitted latency-model fields are backward-compatible and default to zero/false, and each applied default is recorded in `summary.latency_metadata.defaults_used`.

## Temperature behavior

Set `propagation.effects.env_effects=true` and provide per-segment `path.segments[].temp_c`.

When enabled, propagation delay is computed with a temperature-adjusted effective group index:

- Reference temperature: `20 C`
- Group-delay coefficient: `7e-6 / C`
- Default temperature spread for statistical estimate: `sigma=1 C`

The spread output is deterministic for a fixed `runtime.seed`, and reports:

- `p05_s`
- `p50_s`
- `p95_s`
- `std_s`

## Validation tests

Run targeted latency checks:

```bash
python -m pytest -q tests/test_latency_temperature.py tests/analytic/test_latency_hft_routes.py
```

These tests lock:

- monotonic increase in latency for hotter segments (with env effects enabled)
- deterministic spread estimate for the same seed
- route-length propagation baseline against `length * n_group / c`

## Runtime benchmarking

Use the benchmark script:

```bash
python scripts/benchmark_simulate.py --mode general --repeat 3
```

Custom set + JSON output:

```bash
python scripts/benchmark_simulate.py \
  --mode general \
  --spec src/fiber_link_sim/schema/examples/hft_chicago_new_jersey.json \
  --spec src/fiber_link_sim/schema/examples/hft_london_frankfurt.json \
  --repeat 5 \
  --json /tmp/sim_bench.json
```

Phys-pipeline-specific execution benchmark (sequential vs DAG cache modes):

```bash
python scripts/benchmark_simulate.py \
  --mode phys-pipeline \
  --spec src/fiber_link_sim/schema/examples/hft_chicago_new_jersey.json \
  --repeat 3 \
  --warmup 1 \
  --cache-root /tmp/fiber_link_sim_phys_pipeline_cache
```

The output table reports `min/mean/p95/max` per spec.

## Notes on fast optimization backends

If wrapper-level optimization needs faster inner loops:

- keep this repo as contract/physics source of truth
- add a new propagation backend behind the existing backend interface
- keep public schemas stable
- validate new backend fidelity with regression tests versus `builtin_ssfm`

A practical workflow is to run broad search with a faster backend, then re-score top candidates with `builtin_ssfm`.

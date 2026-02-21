# Schema README (SimulationSpec / SimulationResult)

This folder defines the **public contract** between:
- the **physics engine repo** (this repo), and
- the **UI/MCP/orchestration repo** (separate).

If agents touch anything, **they should not change the meaning of fields silently**. Version the spec (`v`) for any breaking change.

## Where the schema lives (src-style repo)

Authoritative copies ship with the package:

- `src/fiber_link_sim/schema/simulation_spec.schema.v0.3.json`
- `src/fiber_link_sim/schema/simulation_result.schema.v0.3.json`

A human-facing mirror can exist at repo root (`schema/`) but should be generated from the authoritative copy, not hand-edited.

## Philosophy

- MCP/UI **chooses parameters** and orchestrates runs.
- Physics repo **owns the truth** of what those parameters mean and returns deterministic results.
- Large arrays are returned as **artifact references**, not embedded in JSON.

---

## SimulationSpec fields (what they mean, and why they exist)

### `v`
Spec version string. Required so UI/MCP can detect breaking changes.

### `scenario` (optional)
Non-physics metadata for the product/UI: name/description/tags and arbitrary metadata for grouping or bookkeeping.
It must not change physics.

### `path`
A link is a sequence of segments:
- `segments[i].length_m` contributes to propagation delay and span loss.
- `segments[i].temp_c` is applied to propagation latency when `propagation.effects.env_effects = true` using a deterministic temperature-aware group-delay model.
- `geo.enabled` and `geo.polyline_wgs84` exist for the routing product; physics can ignore them in v0.2.

### `fiber`
Physical medium parameters:
- `alpha_db_per_km`: attenuation
- `beta2_s2_per_m`, `beta3_s3_per_m`: dispersion terms
- `gamma_w_inv_m`: Kerr nonlinearity
- `pmd_ps_sqrt_km`: PMD coefficient (only applied if enabled)
- `n_group`: group index (propagation latency)

### `spans`
How the route is divided into spans and how loss is handled.
- `mode = from_path_segments` means each segment is treated as a span.
- `mode = fixed_span_length` uses `span_length_m` to partition total length.
- `amplifier` describes the amplifier policy:
  - `type=none` → no amplifier
  - `type=edfa` → EDFA model with ASE, requires `noise_figure_db`
  - `mode=auto_gain` → gain chosen to compensate span loss (bounded by `max_gain_db`)
  - `mode=fixed_gain` → use `fixed_gain_db`
  - **Implementation:** OptiCommPy adapter maps auto-gain/fixed-gain into channel amplification behavior and tracks the
    requested per-span gain for deterministic scaling.

### `signal`
Defines modulation and framing (latency depends on rate + framing, not just modulation name).
- `format`: coherent_qpsk / imdd_ook / imdd_pam4
- `symbol_rate_baud`: sets line rate and impacts serialization delay
- `rolloff`: pulse shape rolloff
- `n_pol`: 2 for coherent DP, 1 for IM/DD
- `frame`: payload/preamble/pilot bit counts for serialization and DSP assumptions

### `transceiver`
Front-end assumptions:
- `tx.laser_linewidth_hz`: phase noise (coherent primarily)
- `tx.launch_power_dbm`: launch power per channel
- `rx.coherent`: must match modulation format (enforced by schema)
- `rx.lo_linewidth_hz`: LO phase noise (coherent)
- `rx.adc.sample_rate_hz`, `rx.adc.bits`: digital sampling assumptions. The receiver front-end
  resamples the waveform to `sample_rate_hz` and applies a uniform quantizer with `bits` levels
  (full-scale is set by the maximum absolute sample magnitude; complex signals quantize I/Q separately).
- `rx.noise.thermal`, `rx.noise.shot`: toggle photodetection noise sources

### `processing`
User-configurable DSP and FEC chain.
- `dsp_chain`: ordered list of blocks with `enabled` and `params`.
- `synchronization`: explicit timing/sync policy (`timing_recovery`, `pilot_assisted`, `pilot_update_interval_symbols`, `phase_search_enabled`).
- `fec`: optional LDPC decode; if `enabled=false` then scheme is `none` and rate is 1.0. When LDPC is enabled,
  `fec.params` must include a parity-check matrix `H` plus decoder settings such as `max_iter` (or legacy
  `max_iters`) and `alg` (`"SPA"` or `"MSA"`).
- `autotune` (optional): bounded internal tuning in physics (small inner-loop); MCP should still own larger search.

### `propagation`
How fiber propagation is simulated.
- `model`: scalar_glnse or manakov
- `backend`: backend identifier (v0.2 supports builtin_ssfm only)
- `effects`: toggles (dispersion, nonlinearity, ase, pmd, env_effects)
  - **Implementation:** dispersion → OptiCommPy `D`, nonlinearity → `gamma`, ASE → EDFA vs ideal amp; PMD wired into adapter parameters.
  - `env_effects=true` enables a temperature-adjusted propagation latency calculation based on `path.segments[].temp_c`.
- `environment`: explicit environment defaults/variance for deterministic latency spread modeling (`temperature_ref_c`, `temperature_sigma_c`, `vibration_sigma_ps`).
- `ssfm`: numerical step size controls (dz_m, step_adapt)

### `latency_model`
Controls how latency is broken down in the Metrics stage.
- `serialization_weight`: multiplier on bit-serialization terms.
- `processing_weight`: multiplier applied to `runtime.n_symbols / signal.symbol_rate_baud` to estimate processing time.
- `processing_floor_s`: minimum processing latency applied even for tiny runs.
- `include_queueing_in_total`, `include_processing_in_total`: explicit aggregation policy switches for `total_s`.
- `framing`: explicit framing/overhead assumptions.
  - `include_preamble_bits`, `include_pilot_bits`: include those frame fields in a separate framing term.
  - `fec_overhead_mode`: `none`, `auto_from_code_rate`, or `fixed_ratio`.
  - `fec_overhead_ratio`: required for `fixed_ratio`.
- `queueing`: explicit buffering assumptions (`ingress_buffer_s + egress_buffer_s + scheduler_tick_s`).
- `hardware_pipeline`: fixed hardware delays (`tx_fixed_s + rx_fixed_s + dsp_fixed_s + fec_fixed_s`).

Latency formulas (seconds):
- `serialization_s = payload_bits / (symbol_rate_baud * bits_per_symbol) * serialization_weight`
- `framing_overhead_s = framing_bits / (symbol_rate_baud * bits_per_symbol) * serialization_weight`
- `queueing_s = ingress_buffer_s + egress_buffer_s + scheduler_tick_s`
- `hardware_pipeline_s = tx_fixed_s + rx_fixed_s + dsp_fixed_s + fec_fixed_s`
- `total_s = propagation_s + serialization_s + framing_overhead_s + dsp_group_delay_s + fec_block_s + hardware_pipeline_s + queueing_s + processing_s`

### `runtime`
Controls reproducibility and compute.
- `seed`: required for deterministic runs
- `n_symbols`, `samples_per_symbol`: simulation length and sampling
- `max_runtime_s`: compute budget guardrail

### `outputs`
Controls artifact emission.
- `artifact_level`: none/basic/debug
- `return_waveforms`: whether to emit waveform artifacts (still by reference)
- `artifacts`: explicit artifact-family selection list (`auto`, `constellation`, `phase_error_trace`, `eye_diagram`, `psd`, `osnr_vs_span`, `evm_vs_distance`, `ber_waterfall`)

---

## SimulationResult fields (what MCP/UI should expect)

- `status`: success or error (mutually exclusive summary/error)
- `summary`: metrics + latency budget + throughput numbers (small JSON)
- `summary.latency_s`: structured `LatencyBudget` with explicit modeled terms (`propagation_s`, `serialization_s`, `framing_overhead_s`, `dsp_group_delay_s`, `fec_block_s`, `hardware_pipeline_s`, `queueing_s`, `processing_s`, `total_s`)
- `summary.latency_metadata`: assumptions, inputs, defaults, and schema version for the latency budget (includes deterministic propagation spread percentiles when env effects are enabled). Backward-compat defaults are recorded in `defaults_used`.
- `error`: structured error info for failed runs
- `provenance`: versions/hashes/seed/runtime/backend/model
- `warnings`: non-fatal issues (e.g., equalizer non-convergence)
- `artifacts`: references to plots/data
- `best_found_spec_patch`: optional patch if autotune ran

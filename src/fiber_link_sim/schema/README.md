# Schema README (SimulationSpec / SimulationResult)

This folder defines the **public contract** between:
- the **physics engine repo** (this repo), and
- the **UI/MCP/orchestration repo** (separate).

If agents touch anything, **they should not change the meaning of fields silently**. Version the spec (`v`) for any breaking change.

## Where the schema lives (src-style repo)

Authoritative copies ship with the package:

- `src/fiber_link_sim/schema/simulation_spec.schema.v0.1.json`
- `src/fiber_link_sim/schema/simulation_result.schema.v0.1.json`

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
- `segments[i].temp_c` is available for future environment modeling (only applied if `propagation.effects.env_effects = true`).
- `geo.enabled` and `geo.polyline_wgs84` exist for the routing product; physics can ignore them in v0.1.

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
- `fec`: optional LDPC decode; if `enabled=false` then scheme is `none` and rate is 1.0.
- `autotune` (optional): bounded internal tuning in physics (small inner-loop); MCP should still own larger search.

### `propagation`
How fiber propagation is simulated.
- `model`: scalar_glnse or manakov
- `backend`: backend identifier (v0.1 supports builtin_ssfm only)
- `effects`: toggles (dispersion, nonlinearity, ase, pmd, env_effects)
  - **Implementation:** dispersion → OptiCommPy `D`, nonlinearity → `gamma`, ASE → EDFA vs ideal amp; PMD/env toggles
    are wired into adapter parameters for future modeling.
- `ssfm`: numerical step size controls (dz_m, step_adapt)

### `runtime`
Controls reproducibility and compute.
- `seed`: required for deterministic runs
- `n_symbols`, `samples_per_symbol`: simulation length and sampling
- `max_runtime_s`: compute budget guardrail

### `outputs`
Controls artifact emission.
- `artifact_level`: none/basic/debug
- `return_waveforms`: whether to emit waveform artifacts (still by reference)

---

## SimulationResult fields (what MCP/UI should expect)

- `status`: success or error (mutually exclusive summary/error)
- `summary`: metrics + latency + throughput numbers (small JSON)
- `error`: structured error info for failed runs
- `provenance`: versions/hashes/seed/runtime/backend/model
- `warnings`: non-fatal issues (e.g., equalizer non-convergence)
- `artifacts`: references to plots/data
- `best_found_spec_patch`: optional patch if autotune ran

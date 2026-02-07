# QPSK Long-Haul Roadmap (Spec → Stage Capabilities)

This roadmap captures the **required capabilities** for coherent QPSK long-haul simulations, mapped to the current
`SimulationSpec` schema, along with acceptance criteria per stage. It is intended to align the pipeline described in
[physics_context](../refs/physics_context.md) and [phys_pipeline_usage](../refs/phys_pipeline_usage.md) with the schema contract in
`src/fiber_link_sim/schema/simulation_spec.schema.v0.1.json`.

## Reference Baselines

This roadmap anchors the coherent QPSK long-haul target to a small set of reference baselines so the OptiCommPy-backed
implementation remains grounded in known behavior before we expand or tune parameters.

**Primary baseline (OptiCommPy examples/docs)**

- **OptiCommPy example notebooks/docs are the first-line reference** for the coherent QPSK long-haul chain. Use the
  OptiCommPy canonical flow as the baseline mapping for stage ordering and expected metrics plumbing:
  `simpleWDMTx → manakovSSF → pdmCoherentReceiver → DSP → metrics`.
- The intent is to mirror OptiCommPy defaults (e.g., symbol rates, pulse shaping, SSFM step sizing, DSP block
  order) wherever compatible with the `SimulationSpec`, and then document any deliberate deviations in ADRs.

**Secondary reference categories (sanity bounds & trends)**

- **Textbook fiber systems** (e.g., Govind P. Agrawal, *Fiber-Optic Communication Systems*) for expected dispersion,
  nonlinearity, and OSNR vs. reach trends.
- **Coherent systems fundamentals** (e.g., Ip & Kahn coherent receiver/DSP papers) for DSP block ordering and BER vs.
  OSNR expectations.
- **GN-model / nonlinear impairment studies** (e.g., Essiambre et al. papers on GN/NLI models) for launch-power sweep
  behavior and optimal power region trends.

These secondary sources are used to sanity-check OSNR/BER/launch-power trends and do not supersede the OptiCommPy
baseline implementation decisions.

## Stage-by-stage capability map

> **Legend:** Schema paths use dotted notation (e.g., `signal.format`). All schema references are in
> `src/fiber_link_sim/schema/simulation_spec.schema.v0.1.json`.

### TxStage (bits → symbols → shaped waveform)

**Required capabilities**

| Capability | Spec fields | Notes |
| --- | --- | --- |
| Modulation format selection (QPSK, IM/DD variants for regression) | `signal.format` | QPSK for long-haul; IM/DD formats used for regression. |
| Symbol rate + pulse shaping | `signal.symbol_rate_baud`, `signal.rolloff` | Roll-off is required for RRC-style shaping. |
| Polarization configuration | `signal.n_pol` | Must be 2 for coherent QPSK (schema constraint). |
| Frame structure (payload/preamble/pilots) | `signal.frame.payload_bits`, `signal.frame.preamble_bits`, `signal.frame.pilot_bits` | Defines framing. |
| Launch power | `transceiver.tx.launch_power_dbm` | Optical launch power. |
| TX laser linewidth (phase noise source) | `transceiver.tx.laser_linewidth_hz` | Required for coherent links. |
| Deterministic source bits | `runtime.seed`, `runtime.n_symbols` | Seed drives deterministic symbol generation. |

**Acceptance criteria**

- **Inputs:** `signal`, `transceiver.tx`, `runtime`.
- **Outputs:** deterministic optical-domain samples or refs (e.g., symbols + shaped waveform) for the next stage.
- **Metrics:** optional TX diagnostics (e.g., average launch power confirmation).
- **Determinism:** identical `runtime.seed` + same spec → identical symbol sequence and waveform values (within float tolerance).

### ChannelStage (fiber propagation + spans + amplification)

**Required capabilities**

| Capability | Spec fields | Notes |
| --- | --- | --- |
| Fiber attenuation + dispersion + nonlinearity | `fiber.alpha_db_per_km`, `fiber.beta2_s2_per_m`, `fiber.beta3_s3_per_m`, `fiber.gamma_w_inv_m` | `beta3` optional; `beta2` required. |
| PMD parameterization | `fiber.pmd_ps_sqrt_km` | Used only if PMD is enabled. |
| Group index for latency | `fiber.n_group` | Supports propagation delay accounting. |
| Path geometry / segment lengths | `path.segments[].length_m` | Used to build total path length and optional span splitting. |
| Span plan | `spans.mode`, `spans.span_length_m` | Controls span construction. |
| Amplifier behavior + ASE | `spans.amplifier.type`, `spans.amplifier.mode`, `spans.amplifier.noise_figure_db`, `spans.amplifier.max_gain_db`, `spans.amplifier.fixed_gain_db` | Implemented in OptiCommPy adapter (auto-gain uses span loss bounded by `max_gain_db`, fixed-gain uses `fixed_gain_db`, ASE toggled via EDFA vs ideal amp). |
| Propagation model selection | `propagation.model`, `propagation.backend` | QPSK long-haul typically uses `manakov` + `builtin_ssfm`. |
| Effect toggles | `propagation.effects.dispersion`, `propagation.effects.nonlinearity`, `propagation.effects.ase`, `propagation.effects.pmd`, `propagation.effects.env_effects` | Implemented in OptiCommPy adapter (dispersion → `D`, nonlinearity → `gamma`, ASE → EDFA vs ideal amp; PMD/env toggles tracked for future modeling). |
| SSFM step control | `propagation.ssfm.dz_m`, `propagation.ssfm.step_adapt` | Step size/adaptation for SSFM. |

**Acceptance criteria**

- **Inputs:** `path`, `fiber`, `spans`, `propagation`, `runtime.seed`.
- **Outputs:** received optical field (or reference) after all spans + noise.
- **Metrics:** OSNR/ESNR proxies or span-level diagnostics as available.
- **Determinism:** fixed seed + identical spec → same noise realization and signal evolution (within tolerance).

### RxFrontEndStage (coherent receiver + ADC)

**Required capabilities**

| Capability | Spec fields | Notes |
| --- | --- | --- |
| Coherent vs IM/DD selection | `transceiver.rx.coherent` | For long-haul QPSK, must be `true`. |
| LO laser linewidth | `transceiver.rx.lo_linewidth_hz` | Drives phase noise at the receiver. |
| ADC sampling + quantization | `transceiver.rx.adc.sample_rate_hz`, `transceiver.rx.adc.bits` | Digital sampling and quantization. |
| Receiver noise toggles | `transceiver.rx.noise.thermal`, `transceiver.rx.noise.shot` | Enable/disable noise components. |

**Acceptance criteria**

- **Inputs:** optical field from channel + `transceiver.rx`.
- **Outputs:** digitized electrical samples (I/Q for coherent) and optionally timing metadata.
- **Metrics:** ADC utilization or clipping indicators (if available).
- **Determinism:** same seed + noise toggles → identical noise samples and quantization results.

### DSPStage (resample → matched filter → CD comp → EQ → CPR → demap)

**Required capabilities**

| Capability | Spec fields | Notes |
| --- | --- | --- |
| DSP chain ordering + enablement | `processing.dsp_chain[].name`, `processing.dsp_chain[].enabled` | The chain is ordered as provided. |
| Block parameters | `processing.dsp_chain[].params` | Block-specific parameters validated in code. |
| Supported blocks | `processing.dsp_chain[].name` | `resample`, `matched_filter`, `cd_comp`, `mimo_eq`, `ffe`, `cpr`, `demap`. |

**Acceptance criteria**

- **Inputs:** digitized samples + `processing.dsp_chain`.
- **Outputs:** recovered symbols/decisions or soft bits (LLRs) for FEC.
- **Metrics:** intermediate diagnostics (EVM, residual dispersion, phase error) when enabled.
- **Determinism:** deterministic DSP initialization; same seed → same estimated taps and decisions.

### FECStage (optional LDPC decode)

**Required capabilities**

| Capability | Spec fields | Notes |
| --- | --- | --- |
| FEC enablement | `processing.fec.enabled` | Determines whether decoding is applied. |
| FEC scheme selection | `processing.fec.scheme` | `none` or `ldpc`. |
| Code rate | `processing.fec.code_rate` | Must be 1.0 when disabled. |
| Scheme-specific parameters | `processing.fec.params` | LDPC config placeholders. |

**Acceptance criteria**

- **Inputs:** soft/hard bits from DSP + `processing.fec`.
- **Outputs:** post-FEC bits + error stats.
- **Metrics:** post-FEC BER/FER when enabled.
- **Determinism:** same seed + same soft bits → identical decode results.

**Current implementation note:** LDPC decoding is now performed via OptiCommPy when FEC is enabled. The
`processing.fec.params` payload must include:
- `H`: parity-check matrix (2D list/array, shape `m x n`).
- `max_iter` (or legacy `max_iters`): maximum decoder iterations.
- `alg`: `"SPA"` or `"MSA"` decoder selection.
- `prec` (optional): numeric precision (defaults to `np.float32`).

### MetricsStage (BER/FER/OSNR/latency)

**Required capabilities**

| Capability | Spec fields | Notes |
| --- | --- | --- |
| Run-time bounds | `runtime.max_runtime_s` | Used to enforce simulation runtime policy. |
| Deterministic metrics | `runtime.seed` | Metrics should be reproducible with fixed seed. |

**Acceptance criteria**

- **Inputs:** stage outputs (DSP/FEC), `outputs`, `runtime`.
- **Outputs:** scalar metrics (BER/FER/OSNR/EVM) and latency breakdown.
- **Metrics:** required fields must be finite and within valid ranges (e.g., BER in [0,1]).
- **Determinism:** same seed/spec → identical summary metrics (within tolerance).

### ArtifactsStage (waveforms + diagnostics)

**Required capabilities**

| Capability | Spec fields | Notes |
| --- | --- | --- |
| Artifact recording | `outputs.artifact_level`, `outputs.return_waveforms` | Controls waveform/constellation artifacts. |
| Deterministic emission | `runtime.seed` | Same inputs → same artifact payloads. |

**Acceptance criteria**

- **Inputs:** stage outputs (Tx/Channel/Rx/DSP), `outputs`.
- **Outputs:** artifact references (NPZ) for waveforms and diagnostics.
- **Determinism:** same seed/spec → identical artifact names and shapes.

## Sanity Checks

Run the following sanity checks to validate end-to-end behavior and metric integrity. Each check should assert the
expected behavior and confirm metric ranges (BER in [0,1], EVM ≥ 0, and OSNR/latency values are finite) to guard
against invalid outputs.

1. **Back-to-back BER ~ 0 (no channel impairments):** Disable dispersion, nonlinearity, ASE, and PMD. Expect BER to be
   approximately zero and within [0,1], with EVM ≥ 0 and finite OSNR/latency metrics.
2. **Dispersion-only improves after CD compensation:** Enable dispersion only, compare BER/EVM before and after
   `cd_comp` in DSP; BER should improve and remain within [0,1], EVM should drop or remain stable, and OSNR/latency
   should remain finite.
3. **ASE-only monotonic BER vs OSNR:** Enable ASE noise only and sweep amplifier noise figure or OSNR target. BER should
   monotonically worsen as OSNR decreases, staying within [0,1], with EVM ≥ 0 and finite latency/OSNR values.
4. **Launch-power sweep shows an optimum:** Sweep launch power across a reasonable range. BER/EVM should show a clear
   optimum (U-shape or minimum) due to linear vs nonlinear trade-offs; BER remains within [0,1], EVM ≥ 0, OSNR/latency
   finite.
5. **DSP should not degrade BER:** Compare BER with the full DSP chain enabled vs a baseline with only essential blocks
   (e.g., matched filter + CD). BER should not worsen with additional DSP blocks; values must stay in [0,1], EVM ≥ 0,
   and OSNR/latency finite.
6. **Deterministic seed reproducibility:** Run the same spec and seed twice; summary outputs (BER, EVM, OSNR, latency)
   must match exactly or within tolerance, and remain within expected ranges (BER in [0,1], EVM ≥ 0, finite OSNR and
   latency).

## Artifacts & Visualization Outputs

Artifacts are controlled by the output flags (`outputs.artifact_level`, `outputs.return_waveforms`) and should follow the
State/large arrays policy: **large arrays are stored as refs** (file paths, artifact keys, blob handles) under State
`refs`, while inline values are reserved for **small, scalar summaries**. Inline payloads should be avoided for heavy
waveforms or dense per-sample traces unless explicitly requested by `outputs.return_waveforms`.

**Artifact list (and stage ownership)**

- **Constellation** — produced in **DSPStage** (post-equalization / post-CPR), recorded in **ArtifactsStage**.
- **Phase error trace** — produced in **DSPStage** (CPR residuals), recorded in **ArtifactsStage**.
- **Eye diagram** — produced in **RxFrontEndStage** (sampled electrical waveform) or **DSPStage** (post-matched-filter),
  recorded in **ArtifactsStage**.
- **PSD / spectrum** — produced in **TxStage** (launch spectrum) and **ChannelStage** (after spans), recorded in
  **ArtifactsStage**.
- **OSNR-vs-span** — produced in **ChannelStage** (span-by-span metrics), recorded in **MetricsStage**.
- **EVM-vs-distance** — produced in **DSPStage** (per-span or per-segment EVM snapshots), recorded in **MetricsStage**.
- **BER waterfall** — produced in **MetricsStage** (aggregate across runs or sweeps), recorded in **MetricsStage**.

## Coverage alignment with existing docs

### Documented pipeline vs schema mapping

- [physics_context](../refs/physics_context.md) outlines the **conceptual blocks** (Tx → Channel → Rx → DSP → FEC → Metrics).
- [phys_pipeline_usage](../refs/phys_pipeline_usage.md) defines the **phys-pipeline stage contract** and maps
  `SimulationSpec` sections to stage configs.
- This roadmap maps those conceptual stages to **schema fields** to ensure each block has explicit inputs.

### Gaps / to-be-clarified items

1. **DAC/driver modeling (TX) and photodiode/analog front-end modeling (RX)**
   - Mentioned conceptually in [physics_context](../refs/physics_context.md), but **no explicit spec fields** exist for
     DAC resolution, modulator characteristics, photodiode responsivity, or TIA/analog filters.
2. **Timing recovery / synchronization configuration (DSP)**
   - DSP chain is configurable via `processing.dsp_chain`, but there are **no explicit, named schema fields** for
     timing recovery or pilot-assisted synchronization (left to `params`).
3. **Latency accounting configuration (Metrics)**
   - Latency breakdown is described in [physics_context](../refs/physics_context.md), yet the schema has **no explicit
     latency model parameters** (e.g., serialization vs processing latency weights).
4. **Environmental effects (Channel)**
   - `propagation.effects.env_effects` is a toggle, but **no spec fields define environment parameters** (temperature
     gradients, vibration), aside from optional `path.segments[].temp_c`.
5. **Artifact definitions (Metrics)**
   - `outputs.artifact_level` and `outputs.return_waveforms` toggle artifacts, but **specific artifact types** (e.g.,
     constellation plots, eye diagrams) are not enumerated in the schema.

These gaps should be resolved either by (a) introducing additional spec fields in a **versioned schema update**, or
(b) documenting the implied defaults and parameter usage inside stage `params` definitions with validation and tests.

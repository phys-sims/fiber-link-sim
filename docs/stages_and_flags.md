# Stages and flags (plain-language guide)

This document explains the simulation pipeline stages and the most important flags in
`SimulationSpec` using non-specialist language. For the authoritative field-by-field contract,
see `src/fiber_link_sim/schema/README.md` and the JSON schemas.

## The pipeline at a glance

Each simulation run is a sequence of stages. Think of it as a conveyor belt where each stage
adds or transforms a signal representation.

1. **Tx (Transmitter)**
   - Creates bits, maps them to symbols, and produces a waveform.
   - Sets modulation format (e.g., QPSK, OOK, PAM4), pulse shaping, and framing.

2. **Channel / Fiber**
   - Models how the signal changes as it travels through fiber spans.
   - Applies attenuation (loss), dispersion (spreading in time), nonlinearity (power-dependent
     distortion), and amplifier noise.

3. **Rx Front-End (Receiver hardware)**
   - Models how the signal is converted back into electrical form.
   - Includes coherent vs. direct-detection hardware and ADC assumptions.

4. **DSP (Digital Signal Processing)**
   - Applies receiver-side algorithms such as timing recovery, equalization, carrier recovery,
     and filtering.
   - The exact DSP chain is configurable and ordered.

5. **FEC (Forward Error Correction)**
   - Optional error-correction decoding (e.g., LDPC).
   - Can be turned off to measure raw (pre-FEC) performance.

6. **Metrics**
   - Computes BER/FER, throughput, latency, and other summary metrics.
   - Produces small JSON outputs and optional artifacts (plots/waveforms).

## Spec flags explained (by intent)

Below are the common flags and what they conceptually do.

### Scenario metadata
`scenario` is non-physics metadata (name, tags, description). It is used for grouping or
bookkeeping and **must not change physics**.

### Path, spans, and fiber
These control how long the link is and how it is segmented.

* `path.segments[]`: Defines the physical length of each segment.
* `spans.mode`: How spans are created.
  - `from_path_segments`: each path segment becomes a span.
  - `fixed_span_length`: breaks the total path into equal-length spans.
* `spans.amplifier`:
  - `type=none`: no amplification.
  - `type=edfa`: erbium-doped fiber amplifier with ASE noise.
  - `mode=auto_gain`: set gain to compensate span loss.
  - `mode=fixed_gain`: apply a constant gain each span.
* `fiber.*`: Physical parameters like attenuation (`alpha_db_per_km`) and dispersion (`beta2`).

### Signal and transceiver
These describe the signal format and the transmitter/receiver hardware assumptions.

* `signal.format`: modulation format (coherent_qpsk / imdd_ook / imdd_pam4).
* `signal.symbol_rate_baud`: line rate; affects latency and spectral occupancy.
* `signal.frame`: how many bits are payload vs. overhead (preamble/pilots).
* `transceiver.tx.*`: launch power and laser linewidth (phase noise).
* `transceiver.rx.*`: coherent vs. IM/DD front-end, LO linewidth, ADC settings.

### Propagation model
Controls how fiber propagation is simulated.

* `propagation.model`: chooses the mathematical model (e.g., `scalar_glnse`, `manakov`).
* `propagation.effects`: toggles physical effects on/off:
  - `dispersion`: time spreading
  - `nonlinearity`: power-dependent distortion
  - `ase`: amplifier noise
  - `pmd`: polarization-mode dispersion
  - `env_effects`: environmental perturbations (future-facing)
* `propagation.ssfm.*`: numerical step sizes for the split-step algorithm.

### Processing (DSP + FEC)
Defines the DSP chain and error correction.

* `processing.dsp_chain[]`: ordered list of DSP blocks with `enabled` and `params`.
* `processing.fec`: turn FEC on/off and choose scheme/rate.
* `processing.autotune`: optional bounded internal tuning (small inner loop only).

### Runtime and reproducibility
Controls compute scale and determinism.

* `runtime.seed`: required; ensures runs are repeatable.
* `runtime.n_symbols`, `runtime.samples_per_symbol`: simulation length/precision.
* `runtime.max_runtime_s`: time budget guardrail.

### Outputs and artifacts
Controls what extra data is returned.

* `outputs.artifact_level`: none / basic / debug.
* `outputs.return_waveforms`: whether to emit waveform artifacts (as references).

## Why these knobs exist

The goal is to make the physics chain transparent and configurable without exposing a raw
black box. Each flag maps to a concrete physical or algorithmic assumption that can be tuned,
turned off, or swapped to explore design trade-offs in a controlled, deterministic way.

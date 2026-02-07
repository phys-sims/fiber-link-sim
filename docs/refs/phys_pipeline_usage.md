# Using phys-pipeline with Fiber Physics

This repo is designed to plug into **phys-pipeline**: stages with immutable configs, a stable state, deterministic execution,
and optional artifact recording.

## Stage decomposition

A typical sequential pipeline:

1. **TxStage**: generate bits/frames → symbols → shaped samples → optical field representation
2. **FiberStage**: propagate over spans (loss + dispersion + nonlinearity + ASE) → received field
3. **RxFrontEndStage**: coherent/IMDD detection + ADC → digital samples
4. **DSPStage**: DSP chain (filtering, CD comp, equalization, CPR, demap) → bits/LLRs
5. **FECStage**: LDPC decode (optional) → post-FEC bits/errors
6. **MetricsStage**: compute BER/FER/OSNR/EVM and latency breakdown
7. **ArtifactsStage**: serialize waveforms/diagnostics to NPZ and emit artifact refs

Each stage should accept a stable `State` object and its own `StageConfig` (derived from sections of `SimulationSpec`),
and return a `StageResult` (state + scalar metrics + optional artifacts).

In this repo, the concrete `SimulationState` and stage configs now *inherit from phys-pipeline base types* to ensure
compatibility with phys-pipeline optimizers and caching tools.

## What is `State`?

**Rule:** the *type* of State stays constant across stages; fields are gradually populated.

Recommended conceptual structure:
- `meta`: seed, run id, spec hash, stage timing, bookkeeping
- `refs`: metadata for blob/artifact references (shape, dtype, role, units)
- `signals`: reference map for signal arrays (tx/optical/rx waveforms, symbols)
- `rx`: non-signal receive outputs (frontend params, decisions/LLRs refs)
- `stats`: scalar metrics and intermediate counters
- `artifacts`: artifact references produced so far

### Arrays vs references (critical for caching)

**Reference-first approach (current):** State holds *BlobRef* strings, not arrays.
- Store arrays as NPZ blobs (via the artifact store).
- State contains refs like `blob://<spec_hash>/blobs/rx_samples-<digest>.npz`.
- Stages load by ref when needed.

This keeps State small and hashable, allowing stage-level caching to work as intended while keeping
large arrays out of hashable payloads.

## Mapping `SimulationSpec` → StageConfigs

- TxStageConfig <- `runtime`, `signal`, `transceiver`
- ChannelStageConfig <- `path`, `fiber`, `spans`, `propagation`, `signal`, `runtime`, `transceiver`
- RxFrontEndStageConfig <- `signal`, `runtime`, `transceiver`
- DSPStageConfig <- `processing`, `signal`, `runtime`, `fiber`, `path`
- FECStageConfig <- `processing`, `signal`
- MetricsStageConfig <- `signal`, `runtime`, `latency_model`, `processing`, `fiber`, `path`
- ArtifactsStageConfig <- `outputs`, `runtime`, `signal`

## Determinism

All randomness must be derived from `runtime.seed`. Each stage derives a deterministic stage RNG (e.g., hashing
`<seed>-<stage name>`) so stage-level randomness is independent but reproducible. If noise is enabled (ASE, thermal,
shot), the same spec+seed must reproduce identical results. Adapter calls use a temporary RNG context so global
NumPy RNG state is preserved after each stage.

## Artifacts vs metrics

- Metrics: small scalars (BER, OSNR, latency numbers).
- Artifacts: waveforms/constellations/eye diagrams/PSD/NPZ dumps.

Keep arrays out of metrics to avoid bloating JSON and breaking downstream consumers.

Artifacts are emitted by **ArtifactsStage** after the main pipeline stages have populated State:
- **TxStage/ChannelStage** → PSD (`tx_psd`, `channel_psd`)
- **RxFrontEndStage** → eye diagram (`rx_eye`)
- **DSPStage** → constellation, phase error, DSP eye (`dsp_constellation`, `dsp_phase_error`, `dsp_eye`)

The artifact store also writes a **run manifest** (`run_manifest.json`) when artifacts are enabled. The manifest
captures stage timings, blob reference metadata, and artifact refs to support sim-utils ingestion and caching.

## Suggested repo layout (src-style)

- `src/fiber_link_sim/`
  - `data_models/` (Pydantic models + stage slices)
  - `schema/` (authoritative JSON schemas)
  - `stages/` (phys-pipeline stages)
  - `simulate.py` (`simulate(spec)->result`)
- `docs/` (context + usage)

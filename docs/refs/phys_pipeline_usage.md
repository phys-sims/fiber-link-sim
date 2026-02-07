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

Each stage should accept a stable `State` object and its own `StageConfig` (derived from sections of `SimulationSpec`),
and return a `StageResult` (state + scalar metrics + optional artifacts).

In this repo, the concrete `SimulationState` and stage configs now *inherit from phys-pipeline base types* to ensure
compatibility with phys-pipeline optimizers and caching tools.

## What is `State`?

**Rule:** the *type* of State stays constant across stages; fields are gradually populated.

Recommended conceptual structure:
- `meta`: seed, run id, spec hash, bookkeeping
- `tx`: bits/symbols references + framing metadata
- `optical`: references to optical-domain signals (field/waveform)
- `rx`: sampled electrical signals, decisions, LLRs
- `metrics`: optional running diagnostics
- `artifacts`: artifact references produced so far

### Arrays vs references (critical for caching)

**MVP approach:** State holds numpy arrays directly.
- Pros: simplest, fastest to implement
- Cons: large objects make hashing/caching expensive and brittle

**Recommended approach:** State holds *BlobRef* strings, not arrays.
- Store arrays as NPZ (or recorder-backed artifacts).
- State contains refs like `artifact://run/<id>/rx_samples.npz`.
- Stages load by ref when needed.

This keeps State small and hashable, allowing stage-level caching to work as intended.

## Mapping `SimulationSpec` → StageConfigs

- TxStageConfig <- `signal`, `transceiver.tx`
- FiberStageConfig <- `path`, `fiber`, `spans`, `propagation`
- RxStageConfig <- `transceiver.rx`
- DSPStageConfig <- `processing.dsp_chain`
- FECStageConfig <- `processing.fec`
- MetricsStageConfig <- `outputs` + latency accounting rules

## Determinism

All randomness must be derived from `runtime.seed`. The pipeline initializes a **root RNG** seeded by `runtime.seed`
and stores it in State (`state.rng`) for traceability. Each stage derives a deterministic stage RNG (e.g., hashing
`<seed>-<stage name>`) so stage-level randomness is independent but reproducible. If noise is enabled (ASE, thermal,
shot), the same spec+seed must reproduce identical results.

## Artifacts vs metrics

- Metrics: small scalars (BER, OSNR, latency numbers).
- Artifacts: waveforms/constellations/eye diagrams/NPZ dumps.

Keep arrays out of metrics to avoid bloating JSON and breaking downstream consumers.

## Suggested repo layout (src-style)

- `src/fiber_physics/`
  - `spec_models.py` (Pydantic models + schema export)
  - `schema/` (authoritative JSON schemas)
  - `stages/` (phys-pipeline stages)
  - `simulate.py` (`simulate(spec)->result`)
- `schema/` (human-facing mirror + examples)
- `docs/` (context + usage)

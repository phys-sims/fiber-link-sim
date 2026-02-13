# Phys-Pipeline Readiness Roadmap (Caching + Scheduling + sim-utils)

This roadmap turns the phys-pipeline review into an actionable plan so **fiber-link-sim** is ready for
upcoming phys-pipeline caching backends, scheduled executors, and the WIP **sim-utils** test harness/ML tooling.
It focuses on **interfaces, determinism, and state/caching semantics** without changing the public spec shape.

## Goals

1. **Phys-pipeline compatibility:** stage configs and state are stable, hashable, and cache-friendly.
2. **Deterministic execution under scheduling:** no reliance on global RNG state; stage-level RNGs only.
3. **Artifact + blob policy:** large arrays are referenced, not embedded in State, to support caching backends.
4. **sim-utils readiness:** provide deterministic, observable hooks for harnessed runs and ML integration.

## Phase 0 — Audit & alignment (now → next sprint)

**Deliverables**

- [x] **State layout alignment doc (current snapshot):** `SimulationState` currently contains
      `meta`, `tx`, `optical`, `rx`, `stats`, `artifacts`, `rng` and hashes `meta/tx/optical/rx/stats` only.
      **Deviations from target shape**: no explicit `refs` or `signals` sections, and large arrays
      (waveforms/samples/symbols) are stored directly under `tx/optical/rx`. **Proposed mapping**:
      - `meta` → `meta` (no change)
      - `tx`/`optical`/`rx` waveforms/samples → `signals` (with refs where possible)
      - `artifacts` → `refs` (keep artifact metadata + ref URIs)
      - `stats` → `stats` (no change)
      - `rng` → move out of hashable state or into `meta.rng_seed` only
- [x] **StageConfig minimality checklist (current snapshot):**
      - **TxStage** needs `runtime` (n_symbols, samples_per_symbol), `signal` (format, rolloff, n_pol, symbol_rate),
        `transceiver.tx` (launch_power_dbm, laser_linewidth_hz).
      - **ChannelStage** needs `path`, `spans`, `fiber`, `propagation` (effects + ssfm dz), `signal` (symbol_rate),
        `runtime.samples_per_symbol`, `transceiver.tx` (launch_power_dbm).
      - **RxFrontEndStage** needs `signal` (symbol_rate), `runtime.samples_per_symbol`, `transceiver.rx` (noise/LO),
        `transceiver.tx` (launch_power_dbm).
      - **DSPStage** needs `processing.dsp_chain`, `signal`, `runtime.samples_per_symbol`, and `fiber` (EDC params).
      - **FECStage** needs `processing.fec`, `signal` (format), `runtime` (n_symbols) for fallback metrics.
      - **MetricsStage** needs `signal`, `runtime`, `latency_model`, `processing.fec`, `fiber`, `path`.
      - **ArtifactsStage** needs `outputs` (artifact_level, return_waveforms), `runtime.samples_per_symbol`,
        `signal.symbol_rate_baud`.
      - **Current gap**: StageConfig classes still hold the full `SimulationSpec`.
- [x] **Determinism map (current snapshot):**
      - **Safe (local RNG)**: `SimulationState.stage_rng` derives a per-stage RNG from `meta.seed`.
      - **Unsafe (global RNG)**: `np.random.seed(...)` in `DSPStage` and OptiCommPy adapters
        (Tx/Channel/Rx Frontend) mutates global state.
      - **Third-party RNG**: OptiCommPy calls rely on `np.random.seed` for repeatability.
      - **Next action**: eliminate all global RNG usage and pass RNG objects or deterministic seeds
        through adapter calls.

**Acceptance criteria**

- ✅ A short doc note in this roadmap listing current state fields and planned renames or aliases (if any).
- ✅ A one-page checklist mapping spec slices to stage configs (inputs only).
- ✅ All RNG usage sites are enumerated and tagged as safe/unsafe for scheduled execution.

## Phase 1 — Cache-ready State & Configs (near-term)

**Work items**

- [x] **Introduce `refs`/`signals` sections in `SimulationState`.**
      Move large arrays into artifact/blob references and store only references in State.
- [x] **Refactor stage outputs to store references** (e.g., waveform refs, rx_samples refs)
      while maintaining the same physics behavior.
- [x] **Make StageConfigs minimal and immutable** (only stage-specific spec slices, no full spec object).
- [x] **Add unit tests** for State hashing determinism with refs (not raw arrays).

**Acceptance criteria**

- State hashing remains deterministic and fast; unit tests cover hash stability.
- StageConfig instances serialize deterministically and are small enough for caching.
- Large arrays are only stored as refs; State no longer contains raw waveforms in steady-state.

## Phase 2 — Determinism under scheduled executors (near-term)

**Work items**

- [x] **Eliminate all global RNG usage** (e.g., `np.random.seed`) in stages or adapters.
- [x] **Pass per-stage RNGs explicitly** through adapter calls where randomness is required.
- [x] **Add determinism tests** that run the pipeline twice with the same seed under a simulated
      “scheduled executor” mode (can be a local test that shuffles stage ordering constraints).

**Acceptance criteria**

- Determinism tests show identical summary metrics for repeated runs (within tolerance).
- No global RNG state is mutated during pipeline execution.

## Phase 3 — Artifact backend + sim-utils hooks (mid-term)

**Work items**

- [x] **Artifact store abstraction:** add a small interface for artifact storage (local path by default)
      to support future caching backends and sim-utils artifact consumers.
- [x] **Explicit artifact metadata schema** (names, shapes, units) to help sim-utils pipeline
      interpret artifacts consistently.
- [x] **Expose a run manifest** (e.g., JSON with stage timing + artifact refs) for harness integration.

**Acceptance criteria**

- Artifacts are stored through an interface that can be swapped for cache-backed stores.
- sim-utils can ingest a run manifest and retrieve artifacts deterministically.

## Phase 4 — Pipeline caching + scheduling integration (when phys-pipeline releases)

**Work items**

- [x] **Integrate phys-pipeline caching backend** and ensure stage-level cache hits occur with ref-based state.
- [x] **Add a scheduled executor path** (or configuration flag) that exercises phys-pipeline scheduling.
- [x] **Remove or gate `_SIMULATION_CACHE`** to avoid conflicts with pipeline caching.

**Acceptance criteria**

- Stage-level caching hits can be observed and verified in tests or logs.
- Scheduled execution produces identical outputs to sequential execution.
- Local `_SIMULATION_CACHE` is disabled or scoped to avoid double caching.

## Cross-cutting QA & docs updates (all phases)

- [x] **Update ADRs** when decisions affect State layout, artifact references, or caching policy.
- [x] **Update `docs/refs/phys_pipeline_usage.md`** with the final ref-based State policy and artifact backend.
- [x] **Add/refresh tests**:
  - Contract tests (example specs validate)
  - Integration tests (end-to-end, status==success)
  - Determinism tests (same spec+seed → same summary)

## Dependencies & coordination notes

- **phys-pipeline caching backend:** required for Phase 4 verification.
- **sim-utils harness/API:** needed to validate artifact manifests and ML workflows.
- **OptiCommPy adapter RNG behavior:** must be confirmed for deterministic per-stage RNG use.

## Risks

- **State refactor complexity:** moving arrays to refs can ripple through adapter code and tests.
- **Caching stability:** StageConfig immutability must be enforced or caching keys may drift.
- **Artifact schema drift:** needs to stay consistent with sim-utils expectations.

## Tracking checklist

- [x] Phase 0 complete
- [x] Phase 1 complete
- [x] Phase 2 complete
- [x] Phase 3 complete
- [x] Phase 4 complete

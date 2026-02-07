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

- [ ] **State layout alignment doc:** confirm `SimulationState` sections match the recommended shape
      (meta/refs/signals/rx/stats) and document any deviations.
- [ ] **StageConfig minimality checklist:** enumerate which `SimulationSpec` slices each stage truly needs
      (Tx, Channel, Rx, DSP, FEC, Metrics, Artifacts).
- [ ] **Determinism map:** list all RNG usage sites (including third-party/OptiCommPy) and confirm no global RNG
      mutations remain.

**Acceptance criteria**

- A short doc note in this roadmap listing current state fields and planned renames or aliases (if any).
- A one-page checklist mapping spec slices to stage configs (inputs only).
- All RNG usage sites are enumerated and tagged as safe/unsafe for scheduled execution.

## Phase 1 — Cache-ready State & Configs (near-term)

**Work items**

- [ ] **Introduce `refs`/`signals` sections in `SimulationState`.**
      Move large arrays into artifact/blob references and store only references in State.
- [ ] **Refactor stage outputs to store references** (e.g., waveform refs, rx_samples refs)
      while maintaining the same physics behavior.
- [ ] **Make StageConfigs minimal and immutable** (only stage-specific spec slices, no full spec object).
- [ ] **Add unit tests** for State hashing determinism with refs (not raw arrays).

**Acceptance criteria**

- State hashing remains deterministic and fast; unit tests cover hash stability.
- StageConfig instances serialize deterministically and are small enough for caching.
- Large arrays are only stored as refs; State no longer contains raw waveforms in steady-state.

## Phase 2 — Determinism under scheduled executors (near-term)

**Work items**

- [ ] **Eliminate all global RNG usage** (e.g., `np.random.seed`) in stages or adapters.
- [ ] **Pass per-stage RNGs explicitly** through adapter calls where randomness is required.
- [ ] **Add determinism tests** that run the pipeline twice with the same seed under a simulated
      “scheduled executor” mode (can be a local test that shuffles stage ordering constraints).

**Acceptance criteria**

- Determinism tests show identical summary metrics for repeated runs (within tolerance).
- No global RNG state is mutated during pipeline execution.

## Phase 3 — Artifact backend + sim-utils hooks (mid-term)

**Work items**

- [ ] **Artifact store abstraction:** add a small interface for artifact storage (local path by default)
      to support future caching backends and sim-utils artifact consumers.
- [ ] **Explicit artifact metadata schema** (names, shapes, units) to help sim-utils pipeline
      interpret artifacts consistently.
- [ ] **Expose a run manifest** (e.g., JSON with stage timing + artifact refs) for harness integration.

**Acceptance criteria**

- Artifacts are stored through an interface that can be swapped for cache-backed stores.
- sim-utils can ingest a run manifest and retrieve artifacts deterministically.

## Phase 4 — Pipeline caching + scheduling integration (when phys-pipeline releases)

**Work items**

- [ ] **Integrate phys-pipeline caching backend** and ensure stage-level cache hits occur with ref-based state.
- [ ] **Add a scheduled executor path** (or configuration flag) that exercises phys-pipeline scheduling.
- [ ] **Remove or gate `_SIMULATION_CACHE`** to avoid conflicts with pipeline caching.

**Acceptance criteria**

- Stage-level caching hits can be observed and verified in tests or logs.
- Scheduled execution produces identical outputs to sequential execution.
- Local `_SIMULATION_CACHE` is disabled or scoped to avoid double caching.

## Cross-cutting QA & docs updates (all phases)

- [ ] **Update ADRs** when decisions affect State layout, artifact references, or caching policy.
- [ ] **Update `docs/refs/phys_pipeline_usage.md`** with the final ref-based State policy and artifact backend.
- [ ] **Add/refresh tests**:
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

- [ ] Phase 0 complete
- [ ] Phase 1 complete
- [ ] Phase 2 complete
- [ ] Phase 3 complete
- [ ] Phase 4 complete

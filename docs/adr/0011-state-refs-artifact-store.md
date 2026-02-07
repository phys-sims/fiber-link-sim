**Title:** Adopt ref-based SimulationState with artifact store + run manifest

- **ADR ID:** 0011
- **Status:** Accepted
- **Date:** 2026-02-08
- **Deciders:** @openai-codex
- **Area:** phys-pipeline
- **Related:** docs/roadmaps/phys_pipeline_readiness.md
- **Tags:** data-model, determinism, caching, testing

### Context
- **Problem statement.** Phys-pipeline caching and sim-utils require hashable, stable State payloads and
  deterministic references for large arrays without embedding raw waveforms in State.
- **In/Out of scope.** This ADR covers State layout, blob reference handling, and artifact manifest output.
  It does not change the public SimulationSpec/SimulationResult schemas.
- **Constraints.** Deterministic runs (same spec+seed), cache-friendly state hashing, and minimal changes
  to the public contract.

### Options Considered
**Option A — Keep arrays in State (status quo)**
- **Description:** Store waveforms/symbols directly under `state.tx/optical/rx`.
- **Pros:** Simple, minimal IO.
- **Cons:** Hashing/caching becomes slow and brittle; large arrays pollute state.

**Option B — Ref-based State + artifact store (chosen)**
- **Description:** Store large arrays in a blob store, keep only references + metadata in State.
- **Pros:** Cache-friendly, deterministic refs, compatible with scheduled executors and sim-utils.
- **Cons:** Extra IO and storage management.

### Decision
- **Chosen option:** Option B.
- **Trade-offs:** Accept modest IO overhead to gain cacheable State and deterministic references.
- **Scope of adoption:** All stages use `signals` refs; artifacts are written via a store abstraction.

### Consequences
- **Positive:** State hashing is stable and small; blob refs include metadata (shape/dtype/role/units);
  run manifests can be consumed by sim-utils.
- **Negative / Mitigations:** Additional storage IO. Use compressed NPZ and keep blob metadata small.
- **Migration plan:** Update StageConfig slices, stages, tests, and docs. No schema changes required.
- **Test strategy:** Unit tests for state hash stability with refs; deterministic RNG context test; existing
  integration/determinism tests continue to validate end-to-end behavior.
- **Documentation:** Update phys-pipeline usage docs and roadmap status.

### Alternatives Considered (but not chosen)
- External cache store only (no local blob store); deferred due to missing phys-pipeline backend.

### Open Questions
- How to integrate phys-pipeline caching backend once available (Phase 4).

### References
- docs/roadmaps/phys_pipeline_readiness.md
- docs/refs/phys_pipeline_usage.md

### Changelog
- 2026-02-08 — Accepted by @openai-codex

---

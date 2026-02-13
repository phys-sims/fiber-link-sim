**Title:** Integrate DagExecutor scheduling + cache backend for Phase 4 readiness

- **ADR ID:** 0014
- **Status:** Accepted
- **Date:** 2026-02-13
- **Deciders:** @openai-codex
- **Area:** phys-pipeline
- **Related:** docs/roadmaps/phys_pipeline_readiness.md
- **Tags:** scheduling, caching, determinism, testing

### Context
- **Problem statement.** Phase 4 of the readiness roadmap requires exercising phys-pipeline scheduled execution,
  proving stage-level cache hits, and preventing conflicts with the legacy in-process `_SIMULATION_CACHE`.
- **In/Out of scope.** In scope: internal execution mode wiring (`SequentialPipeline` vs `DagExecutor`),
  cache backend integration, and tests/docs. Out of scope: public schema changes.
- **Constraints.** Preserve deterministic outputs and keep `SimulationSpec`/`SimulationResult` stable.

### Options Considered
**Option A — Keep sequential-only execution + local process cache**
- **Pros:** Minimal changes.
- **Cons:** Does not verify Phase 4 readiness; no stage-level cache observability.

**Option B — Add optional DagExecutor path with cache backend (chosen)**
- **Description:** Introduce an internal execution switch driven by environment configuration.
  Build a linear `NodeSpec` chain from existing stages and execute through `DagExecutor`.
- **Pros:** Exercises scheduler/caching code paths now; enables deterministic cache-hit validation.
- **Cons:** Additional integration complexity and runtime configuration surface.

### Decision
- **Chosen option:** Option B.
- **Execution modes:**
  - `FIBER_LINK_SIM_PIPELINE_EXECUTOR=sequential` (default)
  - `FIBER_LINK_SIM_PIPELINE_EXECUTOR=dag`
- **Cache controls in DAG mode:**
  - `FIBER_LINK_SIM_PIPELINE_CACHE_BACKEND=disk|shared-disk|none` (default `disk`)
  - `FIBER_LINK_SIM_PIPELINE_CACHE_ROOT=<path>`
- **Conflict mitigation:** automatically disable local `_SIMULATION_CACHE` when DAG mode is active.

### Consequences
- **Positive:** Stage-level cache hits are measurable via node provenance; scheduled execution path is available
  without changing public contracts.
- **Negative / Mitigations:** More internal complexity; mitigated with focused unit tests covering cache-hit
  behavior and sequential-vs-DAG output equivalence.
- **Test strategy:** `tests/test_pipeline_execution_phase4.py` validates (1) cache hits on repeated DAG runs and
  (2) deterministic equality between sequential and DAG execution for the same initial state.
- **Documentation:** Update roadmap, usage docs, and STATUS.

### References
- docs/roadmaps/phys_pipeline_readiness.md
- docs/refs/phys_pipeline_usage.md

### Changelog
- 2026-02-13 — Accepted by @openai-codex

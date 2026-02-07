**Title:** Fail fast when autotune is enabled

- **ADR ID:** 0007
- **Status:** Accepted
- **Date:** 2026-02-07
- **Deciders:** @physics-core
- **Area:** phys-pipeline
- **Related:** PR #000
- **Tags:** api, data-model, testing

### Context
- **Problem statement.** The spec exposes `processing.autotune`, but the pipeline does not implement an autotune loop yet. We need deterministic, explicit behavior without changing the public schema.
- **In/Out of scope.** This ADR governs how the simulator reacts to `processing.autotune.enabled=true`. It does not define a full autotune algorithm or API changes.
- **Constraints.** Maintain public schema stability and deterministic outcomes while providing a clear contract to callers.

### Options Considered
**Option A — Fail fast with `not_implemented`**
- **Description:** Return a structured error before pipeline execution when autotune is enabled.
- **Impact areas:** error handling, tests, documentation.
- **Pros:** explicit, deterministic, avoids hidden partial tuning.
- **Cons:** no autotune capability yet.
- **Risks / Unknowns:** callers must handle error and retry with autotune disabled.
- **Perf/Resource cost:** minimal.
- **Operational complexity:** low.
- **Dependencies / Externalities:** none.

**Option B — Minimal autotune loop**
- **Description:** run a bounded inner loop with limited parameter adjustments.
- **Impact areas:** pipeline stages, metrics, determinism, testing.
- **Pros:** provides early functionality.
- **Cons:** risk of incomplete or incorrect tuning policy, higher maintenance.
- **Risks / Unknowns:** reproducibility across stages and metric stability.
- **Perf/Resource cost:** additional runtime per simulation.
- **Operational complexity:** medium.
- **Dependencies / Externalities:** might require deeper OptiCommPy integration.

### Decision
- **Chosen option:** Option A — Fail fast with `not_implemented`.
- **Trade-offs:** callers cannot use autotune until a formal implementation lands, but behavior is explicit and stable.
- **Scope of adoption:** `simulate()` enforces the policy for any spec with `processing.autotune.enabled=true`.

### Consequences
- **Positive:** deterministic, documented, contract-compatible behavior.
- **Negative / Mitigations:** lack of autotune functionality; tracked for future ADR when implementing autotune.
- **Migration plan:** none; no schema change.
- **Test strategy:** unit test asserts `simulate()` returns `status=error` and `error.code=not_implemented` when autotune is enabled.
- **Documentation:** ADR entry and index update.

### Alternatives Considered (but not chosen)
- Implement a minimal autotune loop without fully validated OptiCommPy integration.

### Open Questions
- What parameter subset and objective function should be supported in the first autotune implementation?

### References
- `processing.autotune` in SimulationSpec schema and README.

### Changelog
- `2026-02-07` — Proposed by @physics-core

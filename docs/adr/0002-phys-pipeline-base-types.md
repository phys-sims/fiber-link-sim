**Title:** Adopt phys-pipeline base types for state and stages

- **ADR ID:** `0002`
- **Status:** `Accepted`
- **Date:** `2025-09-27`
- **Deciders:** `@fiber-physics`
- **Area:** `phys-pipeline`
- **Related:** `docs/refs/phys_pipeline_usage.md`
- **Tags:** `api, data-model, testing`

### Context
- **Problem statement.** The simulator needs to interoperate with phys-pipeline optimization tooling, which expects stages and state to conform to phys-pipeline base types.
- **In/Out of scope.** In scope: Stage/State/StageResult typing and pipeline execution. Out of scope: higher-level optimization logic, UI orchestration.
- **Constraints.** Determinism and stable hashing of State must be preserved; Stage configs must remain immutable for caching.

### Options Considered

**Option A — Wrap phys-pipeline types**
- **Description:** Implement SimulationState as a phys-pipeline State, define Stage configs as StageConfig, and run a SequentialPipeline.
- **Impact areas:** pipeline execution, caching, tests, determinism.
- **Pros:** Compatible with optimization tooling; consistent hashing; minimal surface for external integrations.
- **Cons:** Requires updating pipeline wiring and state hashing.
- **Risks / Unknowns:** Hashing large arrays may be expensive if stored directly in State.
- **Perf/Resource cost:** Slight overhead for hashing; otherwise neutral.
- **Operational complexity:** Low.
- **Security/Privacy/Compliance:** None.
- **Dependencies / Externalities:** phys-pipeline package API stability.

**Option B — Keep bespoke Stage/State types**
- **Description:** Maintain custom Stage/State interfaces and wrap later if needed.
- **Impact areas:** integration risk, future refactor.
- **Pros:** No immediate refactor.
- **Cons:** Blocks phys-pipeline integration; delayed tech debt.
- **Risks / Unknowns:** Higher migration cost later.
- **Perf/Resource cost:** Neutral.
- **Operational complexity:** Medium (dual abstractions).
- **Security/Privacy/Compliance:** None.
- **Dependencies / Externalities:** None.

### Decision
- **Chosen option:** Option A.
- **Trade-offs:** Accept a small hash overhead in exchange for compatibility and deterministic caching.
- **Scope of adoption:** All pipeline stages and state types in this repo.

### Consequences
- **Positive:** phys-pipeline optimizers can reuse the simulator without adapter glue.
- **Negative / Mitigations:** Hashing large arrays is expensive; keep arrays minimal or move to artifact refs later.
- **Migration plan:** Update stage base classes, pipeline builder, and tests to rely on phys-pipeline types.
- **Test strategy:** Unit test State hashing determinism; integration tests validate pipeline outputs.
- **Monitoring & Telemetry:** None.
- **Documentation:** Update pipeline usage notes to reference phys-pipeline types.

### Alternatives Considered (but not chosen)
- Use a dual-adapter layer for both phys-pipeline and custom types (adds complexity without benefit).

### Open Questions
- Should large-array references replace in-memory arrays in State for caching scalability?

### References
- `docs/refs/phys_pipeline_usage.md`

### Changelog
- `2025-09-27` — Proposed/Accepted by @fiber-physics

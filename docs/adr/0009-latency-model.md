**Title:** Define explicit latency model parameters in the SimulationSpec

- **ADR ID:** 0009
- **Status:** Accepted
- **Date:** 2026-02-09
- **Deciders:** @openai-codex
- **Area:** phys-pipeline
- **Related:** PR: latency-model-schema
- **Tags:** data-model, metrics, testing

### Context
- **Problem statement.** Latency reporting used a fixed heuristic inside MetricsStage, making it difficult to reason
  about serialization vs. processing impacts and impossible to tune for different deployment assumptions.
- **In/Out of scope.** In scope: introduce explicit latency model parameters in the spec, surface them in latency
  breakdown computations, and validate behavior with unit tests. Out of scope: any new physical propagation or DSP
  timing models beyond the existing estimators.
- **Constraints.** Must remain deterministic, maintain spec/result contract stability, and keep tests small/fast.

### Options Considered

**Option A — Hard-coded heuristic (status quo)**
- **Description:** Keep using fixed constants in MetricsStage without spec exposure.
- **Impact areas:** MetricsStage only.
- **Pros:** No schema changes.
- **Cons:** Users cannot tune latency assumptions; the breakdown is opaque and brittle.
- **Risks / Unknowns:** Misleading latency reporting across different formats and runtime settings.
- **Perf/Resource cost:** None.
- **Operational complexity:** Low.
- **Security/Privacy/Compliance:** None.
- **Dependencies / Externalities:** None.

**Option B — Explicit latency model parameters (chosen)**
- **Description:** Add a `latency_model` section to SimulationSpec with serialization and processing weights and a
  processing floor, and use these values in MetricsStage.
- **Impact areas:** Spec schema, examples, MetricsStage, docs, tests.
- **Pros:** Transparent, configurable latency breakdown; deterministic and testable; minimal disruption to pipeline.
- **Cons:** Requires spec version bump and updates to example specs.
- **Risks / Unknowns:** Consumers must supply new latency model parameters when adopting v0.2.
- **Perf/Resource cost:** Negligible.
- **Operational complexity:** Low.
- **Security/Privacy/Compliance:** None.
- **Dependencies / Externalities:** None.

### Decision
- **Chosen option:** Option B — add `latency_model` parameters to the spec and apply them in MetricsStage.
- **Trade-offs:** We accept a spec version bump to gain explicit configuration and better transparency.
- **Scope of adoption:** All v0.2 SimulationSpec consumers and MetricsStage latency reporting.

### Consequences
- **Positive:** Latency breakdown can reflect configured behavior; deterministic tests lock expectations.
- **Negative / Mitigations:** Spec changes require updating existing specs; example specs are updated to include
  default weights and floor values.
- **Migration plan:** Update schema to v0.2, add `latency_model` to examples, and update documentation. Existing v0.1
  specs must be migrated by adding latency parameters.
- **Test strategy:** Add unit test to compute exact propagation/serialization/processing totals from a small spec.
- **Monitoring & Telemetry:** None.
- **Documentation:** Update schema README and long-haul roadmap to describe latency model fields.

### Alternatives Considered (but not chosen)
- Keep the heuristic and document it without exposing configuration.

### Open Questions
- None.

### References
- `src/fiber_link_sim/stages/core.py` latency computation
- `src/fiber_link_sim/schema/simulation_spec.schema.v0.2.json`

### Changelog
- `2026-02-09` — Accepted by @openai-codex

---

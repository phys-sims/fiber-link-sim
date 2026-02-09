**Title:** Replace heuristic latency with structured LatencyBudget + metadata

- **ADR ID:** 0012
- **Status:** Accepted
- **Date:** 2026-02-10
- **Deciders:** @openai-codex
- **Area:** metrics
- **Related:** docs/roadmaps/version_1_release.md, docs/adr/0009-latency-model.md
- **Tags:** data-model, metrics, testing

### Context
- **Problem statement.** The latency breakdown in `SimulationResult.summary.latency_s` was a single heuristic
  with limited transparency and no explicit metadata tying assumptions to spec inputs. Version 1 release
  requirements call for a deterministic, stage-aware latency budget with explicit assumptions and defaults.
- **In/Out of scope.** In scope: new `LatencyBudget` structure with named terms, metadata describing inputs
  and defaults, and updated tests/schemas. Out of scope: detailed hardware timing models or runtime profiling.
- **Constraints.** Must preserve determinism, keep spec compatibility, and remain OptiCommPy-first.

### Options Considered
**Option A — Keep heuristic latency fields**
- **Description:** Retain `propagation`, `serialization`, `processing_est`, `total` without metadata.
- **Pros:** No schema changes.
- **Cons:** Does not meet Version 1 release latency requirements; assumptions remain opaque.

**Option B — Structured LatencyBudget + metadata (chosen)**
- **Description:** Replace latency fields with a `LatencyBudget` containing explicit named terms and attach
  `latency_metadata` capturing assumptions, inputs, and defaults.
- **Pros:** Transparent latency components, deterministic derivation, aligns with roadmap requirements.
- **Cons:** Result schema update required.

### Decision
- **Chosen option:** Option B — add structured `LatencyBudget` and `latency_metadata`.
- **Trade-offs:** Accept a result schema update to improve clarity and validation.
- **Scope of adoption:** Metrics stage output, result schema, and validation tests.

### Consequences
- **Positive:** Latency outputs are explicit, explainable, and testable with clear assumptions.
- **Negative / Mitigations:** Consumers must handle the new structured fields; documentation and schema
  references updated accordingly.
- **Migration plan:** Update result schema to v0.2, update latency tests, and document metadata fields.
- **Test strategy:** Add analytic propagation baseline test and latency budget unit test to lock behavior.
- **Documentation:** Update schema README and Version 1 roadmap references.

### Alternatives Considered (but not chosen)
- Store latency metadata in artifacts only; rejected because the contract should expose it directly.

### Open Questions
- Add explicit queueing/buffering models once a scheduling backend is integrated.

### References
- docs/roadmaps/version_1_release.md
- src/fiber_link_sim/latency.py

### Changelog
- 2026-02-10 — Accepted by @openai-codex

---

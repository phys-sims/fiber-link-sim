**Title:** Define long-haul QPSK stage feature coverage via OptiCommPy adapter

- **ADR ID:** `0004`
- **Status:** `Proposed`
- **Date:** `2025-09-27`
- **Deciders:** `@fiber-physics`
- **Area:** `phys-pipeline`
- **Related:** `ADR-0003`
- **Tags:** `api, testing, optics, adapter`

### Context
- **Problem statement.** The long-haul QPSK scenario requires a minimum set of physics stages (SSFM propagation, span loss, EDFA/ASE, coherent RX front-end, dispersion compensation/equalization, carrier recovery). We need to declare which of these are provided by OptiCommPy, how they are invoked through the adapter, and what fallback behavior exists if OptiCommPy lacks a feature—without changing public schemas.
- **In/Out of scope.** This ADR covers stage-level feature coverage and adapter call paths for the long-haul QPSK chain. It does not finalize parameter defaults or public schema changes.
- **Constraints.** Must preserve `SimulationSpec`/`SimulationResult` shape, keep determinism guarantees, and prefer OptiCommPy implementations.

### Options Considered

**Option A — OptiCommPy-first adapter coverage with targeted fallbacks (preferred)**
- **Description:** Provide a dedicated OptiCommPy adapter layer with explicit functions per stage feature; use OptiCommPy wherever it supports the requirement, and implement minimal fallbacks behind the same adapter interface when needed.
- **Impact areas:** adapter module, stage implementations, tests, ADR documentation.
- **Pros:** aligns with repo principle, isolates OptiCommPy API changes, keeps spec stable, deterministic fallbacks.
- **Cons:** requires explicit adapter maintenance and clear gaps documentation.
- **Risks / Unknowns:** OptiCommPy API differences may require additional shims.
- **Perf/Resource cost:** moderate; SSFM cost unchanged.
- **Operational complexity:** low to moderate; adapter centralizes complexity.
- **Security/Privacy/Compliance:** none.
- **Dependencies / Externalities:** OptiCommPy version compatibility.

**Option B — Direct OptiCommPy calls scattered in stages**
- **Description:** Stages call OptiCommPy functions directly with local conversions.
- **Impact areas:** stage code complexity, future refactors.
- **Pros:** fastest to prototype.
- **Cons:** breaks adapter boundary, harder to swap backends, inconsistent unit handling.
- **Risks / Unknowns:** high risk of API drift.
- **Perf/Resource cost:** same as A.
- **Operational complexity:** high.
- **Security/Privacy/Compliance:** none.
- **Dependencies / Externalities:** tight coupling to OptiCommPy internals.

### Decision
- **Chosen option:** Option A.
- **Trade‑offs:** we accept adapter maintenance to keep the stage chain modular and schema stable.
- **Scope of adoption:** all long-haul QPSK required features in the stage chain; adapter functions will be used by stages only.

### Consequences
- **Positive:** explicit mapping from long-haul requirements to OptiCommPy coverage; controlled fallbacks with consistent outputs.
- **Negative / Mitigations:** additional adapter code; mitigated by tests and centralized documentation.
- **Migration plan:** add adapter functions; update stages to call adapter; add tests; no public schema changes.
- **Test strategy:** add unit tests for adapter behavior, integration tests for QPSK pipeline, determinism checks.
- **Monitoring & Telemetry:** track stage warnings when fallback used.
- **Documentation:** update ADR index; keep adapter docs aligned with OptiCommPy usage.

### Stage feature coverage (long-haul QPSK)

| Stage feature | OptiCommPy support | Adapter invocation (planned) | Gap / fallback behavior |
| --- | --- | --- | --- |
| SSFM propagation | Yes. OptiCommPy provides fiber propagation via SSFM utilities. | `OptiCommPyBackend.propagate_ssfm(...)` wraps OptiCommPy fiber/SSFM calls and normalizes units. | If unavailable, fallback to split-step linear-only propagation (dispersion + loss) with documented accuracy limits. |
| Span loss | Yes. OptiCommPy includes span loss/attenuation modeling. | `OptiCommPyBackend.apply_span_loss(...)` invoked per span with deterministic attenuation. | If unavailable, deterministic power scaling per span using attenuation coefficient from spec. |
| EDFA gain + ASE | Yes. OptiCommPy includes EDFA and ASE noise modeling. | `OptiCommPyBackend.apply_edfa(...)` with explicit noise figure, gain, and bandwidth. | If unavailable, fallback to analytic ASE noise injection + gain clamp, keeping deterministic RNG use. |
| Coherent RX front-end | Yes. OptiCommPy supports coherent receiver front-end blocks. | `OptiCommPyBackend.coherent_frontend(...)` returning baseband I/Q and reference signals. | If unavailable, minimal coherent front-end fallback: mixing + LPF with ideal LO. |
| Dispersion compensation / equalization | Yes. OptiCommPy provides dispersion compensation and linear equalizers. | `OptiCommPyBackend.dispersion_compensation(...)` and `OptiCommPyBackend.linear_equalizer(...)` within DSP stage. | If unavailable, fallback to frequency-domain CD compensation + LMS equalizer reference implementation. |
| Carrier recovery | Yes. OptiCommPy includes carrier recovery (phase/frequency recovery). | `OptiCommPyBackend.carrier_recovery(...)` mapping to OptiCommPy CPR functions. | If unavailable, fallback to decision-directed phase tracking with deterministic loop parameters. |

### Validation strategy
- **Determinism tests:** run long-haul QPSK example spec twice with identical seed and assert deterministic key metrics (BER, Q-factor proxy, received power) within tight tolerance.
- **Metric sanity tests:** verify BER/FER are finite and within [0, 1], OSNR/ESNR proxies are finite, and per-stage power levels are finite.
- **Adapter unit tests:** for each adapter method above, use small synthetic signals to validate unit normalization, deterministic noise injection, and fallback activation flags.
- **Integration tests:** pipeline test exercising SSFM, EDFA/ASE, coherent RX, DSP, CPR; assert `status == "success"` and required result fields present.

### Alternatives Considered (but not chosen)
- OptiCommPy direct calls in stages without an adapter.

### Open Questions
- Confirm precise OptiCommPy function/module mappings for each feature and capture in adapter docs.
- Decide default CPR and equalizer parameters for QPSK and record in a follow-up ADR.

### References
- ADR-0003 (OptiCommPy adapter)
- docs/physics_context.md
- docs/phys_pipeline_usage.md

### Changelog
- `2025-09-27` — Proposed by @fiber-physics

---

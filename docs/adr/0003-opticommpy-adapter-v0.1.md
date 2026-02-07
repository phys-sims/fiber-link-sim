**Title:** Implement OptiCommPy adapter for end-to-end v0.1 simulations

- **ADR ID:** `0003`
- **Status:** `Accepted`
- **Date:** `2025-09-27`
- **Deciders:** `@fiber-physics`
- **Area:** `phys-pipeline`
- **Related:** `docs/refs/opticommpy_adapter_notes.md`
- **Tags:** `physics, api, testing`

### Context
- **Problem statement.** The simulator must run end-to-end coherent QPSK, IM/DD OOK, and IM/DD PAM4 using OptiCommPy implementations rather than bespoke placeholders.
- **In/Out of scope.** In scope: Tx/Channel/Rx/DSP/Metrics integration with OptiCommPy and LDPC decode when parity-check matrices are supplied via `processing.fec.params`. Out of scope: advanced FEC tuning and codebook management beyond the supplied matrices.
- **Constraints.** Deterministic runs with a single seed; keep schema stable; avoid scattering OptiCommPy calls outside the adapter.

### Options Considered

**Option A — Central OptiCommPy adapter**
- **Description:** Create an adapter package that builds OptiCommPy parameters, runs tx/channel/rx/dsp, and returns numpy outputs for stages.
- **Impact areas:** stages, tests, documentation, determinism.
- **Pros:** Clear boundary to manage OptiCommPy API changes; consistent unit conversions.
- **Cons:** Adapter must track OptiCommPy updates.
- **Risks / Unknowns:** DSP chain compatibility with future OptiCommPy changes.
- **Perf/Resource cost:** Moderate; OptiCommPy simulations are heavier than analytic approximations.
- **Operational complexity:** Medium.
- **Security/Privacy/Compliance:** None.
- **Dependencies / Externalities:** OptiCommPy runtime and API stability.

**Option B — Mixed OptiCommPy + bespoke physics**
- **Description:** Use OptiCommPy for channel only, leaving tx/rx/dsp as placeholders.
- **Impact areas:** physics fidelity, test realism.
- **Pros:** Faster to implement.
- **Cons:** Violates OptiCommPy-first policy; results less trustworthy.
- **Risks / Unknowns:** High risk of mismatched assumptions.
- **Perf/Resource cost:** Lower.
- **Operational complexity:** Medium.
- **Security/Privacy/Compliance:** None.
- **Dependencies / Externalities:** None.

### Decision
- **Chosen option:** Option A.
- **Trade-offs:** Accept additional runtime to gain alignment with OptiCommPy physics.
- **Scope of adoption:** v0.1 pipeline stages (Tx, Channel, Rx, DSP, Metrics, FEC). FEC uses OptiCommPy LDPC decoding when parity-check inputs are provided via `processing.fec.params`.

### Consequences
- **Positive:** End-to-end simulations now route through OptiCommPy for the core physics chain.
- **Negative / Mitigations:** LDPC decode requires explicit parity-check matrices; simulations must supply `processing.fec.params.H` and decoder configuration to avoid runtime errors.
- **Migration plan:** Extend schema to include LDPC matrices if full decoding is required; update adapter accordingly.
- **Test strategy:** Integration tests for example specs, determinism tests on summary metrics, and unit tests for adapter conversions.
- **Monitoring & Telemetry:** Track runtime and warnings per run.
- **Documentation:** Keep adapter notes updated; document approximations.

### Alternatives Considered (but not chosen)
- Use a separate simulator backend per modulation format (adds maintenance cost).

### Open Questions
- What schema extension is most appropriate for LDPC parity-check matrices or named codebooks?

### References
- `docs/refs/opticommpy_adapter_notes.md`

### Changelog
- `2025-09-27` — Proposed/Accepted by @fiber-physics
- `2026-02-07` — Updated: LDPC decode implemented when parity-check matrices are supplied.

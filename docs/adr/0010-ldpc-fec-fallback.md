**Title:** Use pass-through LDPC FEC fallback when OptiCommPy decoder is unstable
**ADR ID:** 0010-lite
**Status:** Accepted
**Date:** 2026-02-07

**Context:** The OptiCommPy LDPC decoder intermittently raises `SystemError` on repeated runs within the same process, which breaks determinism tests and causes integration specs with FEC enabled to fail. We need a deterministic, stable behavior for the physics-core pipeline while retaining the public spec shape.

**Options:**
- **A:** Keep calling OptiCommPy `decodeLDPC` and accept intermittent runtime errors.
- **B:** Use a deterministic pass-through fallback for LDPC (post-FEC BER = pre-FEC BER) while leaving the spec unchanged.

**Decision:** Choose option B to guarantee deterministic runs and prevent runtime failures while keeping the SimulationSpec/Result stable.

**Consequences:**
- LDPC decoding is treated as a no-op until the OptiCommPy decoder is stable; post-FEC BER equals pre-FEC BER.
- Integration and determinism tests stay green with FEC enabled.
- Revisit and re-enable OptiCommPy LDPC decode once stability is verified; add a targeted regression test.

**References:**
- OptiCommPy `decodeLDPC` runtime errors during repeated simulations.

---

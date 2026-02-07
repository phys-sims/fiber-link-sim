**Title:** Minimal deterministic pipeline + state layout
**ADR ID:** 0001-lite
**Status:** Accepted
**Date:** 2025-09-15

**Context:** The repository needs a working, deterministic simulator that validates the public spec/result contract while the
OptiCommPy-backed physics implementation is being integrated. We still need stable state layout, stage boundaries, and a
repeatable metrics/latency calculation.

**Options:**
- **A)** Build a minimal deterministic pipeline with a stable State object and simplified physics/metrics to satisfy the
  contract and provide baseline tests.
- **B)** Wait for full OptiCommPy integration before implementing any pipeline or tests.

**Decision:** Choose **A** to deliver a working simulator skeleton now. This keeps the spec/result contract enforced, provides
deterministic output, and leaves a clear staging structure for later OptiCommPy integration.

**Consequences:** We add a Tx→Channel→Rx→DSP→FEC→Metrics pipeline with a stable State layout. Metrics/latency are simplified but
deterministic. Tests lock in determinism and FEC passthrough behavior. Future work replaces simplified physics with OptiCommPy
behind the same stage interfaces.

**References:** docs/refs/physics_context.md, docs/refs/phys_pipeline_usage.md

---

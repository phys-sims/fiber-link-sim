**Title:** v1 scope decision for TX/RX analog front-end modeling
**ADR ID:** `0015-lite`
**Status:** `Accepted`
**Date:** `2026-02-20`

**Context:** The QPSK roadmap listed DAC/driver and photodiode/TIA analog-front-end modeling as a contract gap, but v1 focuses on deterministic physics-chain coverage and contract stability.

**Options:**
- Add full analog front-end parameterization in v1.
- Defer analog front-end details and publish explicit assumptions.

**Decision:** Defer DAC/driver and detailed RX analog front-end to post-v1, and record a deterministic assumption in latency metadata that ADC quantization and current photodiode defaults are the v1 approximation.

**Consequences:**
- Keeps v1 schema stable while making scope explicit in outputs.
- Added decision-locking test asserting the out-of-scope assumption appears in `summary.latency_metadata.assumptions`.

**References:**
- docs/roadmaps/qpsk_longhaul.md
- src/fiber_link_sim/latency.py
- tests/test_design_decisions.py

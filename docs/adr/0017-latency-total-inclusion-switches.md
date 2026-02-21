**Title:** Explicit latency total inclusion switches
**ADR ID:** `0017-lite`
**Status:** `Accepted`
**Date:** `2026-02-20`

**Context:** Latency breakdown existed but total aggregation policy for queueing/processing was implicit.

**Options:**
- Keep implicit always-included behavior.
- Add explicit booleans controlling inclusion in `total_s`.

**Decision:** Add `latency_model.include_queueing_in_total` and `latency_model.include_processing_in_total`; when disabled, assumptions are recorded in latency metadata.

**Consequences:**
- Contract now states aggregation policy directly.
- Added decision tests locking assumption strings for each toggle.

**References:**
- src/fiber_link_sim/data_models/spec_models.py
- src/fiber_link_sim/latency.py
- tests/test_design_decisions.py

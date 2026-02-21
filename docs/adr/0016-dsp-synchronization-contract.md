**Title:** Explicit DSP synchronization contract fields
**ADR ID:** `0016-lite`
**Status:** `Accepted`
**Date:** `2026-02-20`

**Context:** Synchronization/timing recovery behavior existed only as free-form DSP block params.

**Options:**
- Continue using ad hoc `dsp_chain[].params` keys.
- Add first-class synchronization fields to the versioned spec.

**Decision:** Add `processing.synchronization` with explicit fields (`timing_recovery`, `pilot_assisted`, `pilot_update_interval_symbols`, `phase_search_enabled`) and wire this through DSP stage slices.

**Consequences:**
- Synchronization intent is explicit and schema-validated.
- Stage config wiring preserves modular DSP implementation.

**References:**
- src/fiber_link_sim/data_models/spec_models.py
- src/fiber_link_sim/stages/core.py

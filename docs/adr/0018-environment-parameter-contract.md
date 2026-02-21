**Title:** Environment parameterization for channel effects
**ADR ID:** `0018-lite`
**Status:** `Accepted`
**Date:** `2026-02-20`

**Context:** `env_effects` toggle existed without explicit environment parameter fields.

**Options:**
- Keep fixed hidden constants.
- Expose explicit environment parameters in the schema.

**Decision:** Add `propagation.environment` with `temperature_ref_c`, `temperature_sigma_c`, and `vibration_sigma_ps`; latency propagation and spread estimation now consume these values.

**Consequences:**
- Environment assumptions move from hidden constants to explicit contract.
- Backends can grow into richer environment modeling without changing top-level shape.

**References:**
- src/fiber_link_sim/data_models/spec_models.py
- src/fiber_link_sim/latency.py

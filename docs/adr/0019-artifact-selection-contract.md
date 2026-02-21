**Title:** Explicit artifact selection list in outputs contract
**ADR ID:** `0019-lite`
**Status:** `Accepted`
**Date:** `2026-02-20`

**Context:** Artifact output level existed, but artifact families were not explicitly contract-enumerated.

**Options:**
- Keep implicit artifact behavior tied only to level/waveform flag.
- Add explicit artifact family enumeration in schema.

**Decision:** Add `outputs.artifacts` as an enum list with `auto` default and named artifact families. ArtifactsStage now gates generation by selection.

**Consequences:**
- API clients can request deterministic artifact subsets.
- Artifact coverage is explicit and versioned in schema.

**References:**
- src/fiber_link_sim/data_models/spec_models.py
- src/fiber_link_sim/stages/core.py
- docs/roadmaps/qpsk_longhaul.md

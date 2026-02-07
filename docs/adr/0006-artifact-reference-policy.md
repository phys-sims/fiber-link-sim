**Title:** Artifact reference policy for waveforms
**ADR ID:** 0006-lite
**Status:** Accepted
**Date:** 2026-02-07

**Context:** The simulator must emit optional artifacts (waveforms/diagnostics) without bloating JSON payloads or breaking
downstream caching. Outputs are controlled by `outputs.artifact_level` and `outputs.return_waveforms`, and artifacts must be
portable references rather than inlined arrays.

**Options:**
- **Embed arrays in `SimulationResult.artifacts`:** simplest to inspect but breaks the public contract (large JSON, brittle).
- **Reference external blobs (npz files) via artifact refs:** keeps JSON small and supports caching.

**Decision:** Emit waveform artifacts only when `artifact_level != "none"` and `return_waveforms == true`, storing arrays as
compressed NPZ files under a deterministic `artifacts/<spec_hash>/` directory and returning `artifact://` references in the
result payload.

**Consequences:** `SimulationResult.artifacts` can be empty. Downstream tools must resolve `artifact://` refs to retrieve
waveforms. Unit tests assert presence/absence based on output flags.

**References:** `docs/refs/phys_pipeline_usage.md`, `src/fiber_link_sim/schema/README.md`.

---

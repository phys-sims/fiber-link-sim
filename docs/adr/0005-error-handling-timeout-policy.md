**Title:** error handling & timeout policy
**ADR ID:** 0005-lite
**Status:** Accepted
**Date:** 2026-02-07

**Context:** The simulator must return structured error results for runtime failures and enforce
`runtime.max_runtime_s` as a compute budget guardrail. We need deterministic, stable error codes and
tests that lock the behavior.

**Options:**
- **A:** Let exceptions bubble and rely on callers to catch timeouts, risking inconsistent error
  reporting and missed budget enforcement.
- **B:** Centralize runtime exception handling and timeout enforcement inside `simulate()`, mapping
  failures to `ErrorInfo` codes with consistent provenance.

**Decision:** Choose option B. `simulate()` wraps pipeline execution, maps unexpected exceptions to
`runtime_error`, enforces `max_runtime_s` with a timeout guard, and returns structured errors with
provenance populated.

**Consequences:** Callers always receive `SimulationResult` on runtime failure or timeout. Timeouts
are enforced centrally; long-running pipeline work may still complete in the background, but results
are discarded. The behavior is validated by unit tests for runtime error mapping and timeout
handling.

**References:**
- `tests/test_simulation_contracts.py::test_simulation_runtime_error_returns_structured_result`
- `tests/test_simulation_contracts.py::test_simulation_timeout_returns_structured_result`

---

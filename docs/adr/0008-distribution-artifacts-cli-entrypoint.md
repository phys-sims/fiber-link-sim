**Title:** `distribution artifacts & CLI entrypoint`
**ADR ID:** `0008-lite`
**Status:** `Accepted`
**Date:** `2026-02-07`

**Context:** The simulator ships JSON schemas and example specs that downstream tooling must load
from the installed package. We also want a small command-line entrypoint for running simulations
directly from a spec file without re-implementing file loading or result serialization in
consumers.

**Options:**
- A) Keep schemas/examples on disk only, and require consumers to locate files in the repository.
- B) Package schemas/examples as distribution data and provide a CLI entrypoint for direct use.

**Decision:** Choose option B so packaged installs can reliably access schema artifacts via
`importlib.resources`, and the CLI can invoke the existing `simulate()` entrypoint with minimal
wrapper logic.

**Consequences:** Packaging configuration now includes schema/example JSON files, and a new CLI
entrypoint is exposed for `fiber-link-sim`. Validation is covered by a unit test that loads an
example spec via `importlib.resources`, and by the standard pre-commit, mypy, and pytest checks.

**References:** `pyproject.toml`, `src/fiber_link_sim/cli.py`, `tests/test_package_data.py`.

---

# CI Checklist

Use this checklist before opening or updating a PR to keep CI green.

## Required checks (must pass before PR)

- `python -m pre_commit run -a`
- `python -m mypy src`
- `python -m pytest -q`

These commands are the CI gates. They **must** pass locally (or in the repo’s CI runner) before a PR is ready.

## Minimal fast checks for local iteration

If full runs are too heavy while iterating, run focused checks locally and then return to the full
required commands above before opening/updating a PR. Examples:

- `python -m pre_commit run -a` (can be run any time to catch formatting issues early)
- `python -m mypy src` (type check only the main package)
- `python -m pytest -q tests/test_simulation_contracts.py` (run a single fast test module)

Always complete the full required checks before you consider a PR ready.

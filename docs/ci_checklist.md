# CI Checklist

Use this checklist before opening or updating a PR to keep CI green.

## Required checks (must pass before PR)

- `python -m pre_commit run -a`
- `python -m mypy src`
- `python -m pytest -q -m "not slow" --durations=10 --cov=fiber_link_sim --cov-report=term-missing:skip-covered`

These commands are the CI gates. They **must** pass locally (or in the repo’s CI runner) before a PR is ready.

## Minimal fast checks for local iteration

If full runs are too heavy while iterating, run focused checks locally and then return to the full
required commands above before opening/updating a PR. Examples:

- `python -m pre_commit run -a` (can be run any time to catch formatting issues early)
- `python -m mypy src` (type check only the main package)
- `python -m pytest -q -m "not slow" --durations=10 --cov=fiber_link_sim --cov-report=term-missing:skip-covered` (run the fast suite with coverage; default)
- `python -m pytest -q -m slow --durations=10` (run slow tests only)
- `python -m pytest -q -m "slow or not slow" --durations=10` (run the full suite)

Always complete the full required checks before you consider a PR ready.

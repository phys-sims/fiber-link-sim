# fiber-link-sim

A modular, reproducible physics-based simulator for fiber-optic communication links

## Installation

```bash
pip install -e .
```

## Testing

Fast tests (default in pytest config):

```bash
pytest -m "not slow" --durations=10
```

Slow tests only:

```bash
pytest -m slow --durations=10
```

Full suite (override defaults if you need slow tests included):

```bash
pytest
```

Note: pytest defaults to `-m "not slow" --durations=10`. To include slow tests in the full
suite, run `pytest -m "slow or not slow" --durations=10`.

# fiber-link-sim

Physics-first simulator core for fiber‑optic communication links.
This repository provides the deterministic physics engine and stable `SimulationSpec → SimulationResult`
contract used by upstream orchestration/UI layers.

## What this project is

* **Physics core only**: Implements the link physics and signal processing pipeline; external tools
  orchestrate runs, sweeps, and visualization.
* **Stable contracts**: JSON Schema + Pydantic models define the public input/output API and are
  versioned to prevent breaking changes.
* **Deterministic**: Same spec + same seed → same results (within floating-point tolerances).
* **Modular pipeline**: Staged chain (Tx → Channel → Rx Front-End → DSP → FEC → Metrics) to keep
  blocks swappable without changing spec shape.

## Who should use this repo

* Researchers validating **link budgets, impairments, and DSP behavior** in a reproducible way.
* Tooling teams integrating a **SimulationSpec/SimulationResult** API into orchestrators or UIs.
* Developers who need a **deterministic, modular physics backend** without owning the full DSP stack.

## High-level architecture

1. **SimulationSpec** is validated (Pydantic + JSON Schema).
2. **Sequential pipeline** runs the configured stages with deterministic RNG.
3. **SimulationResult** is produced and validated against the result model.

Key references for deeper details live in:

* `docs/physics_context.md`
* `docs/phys_pipeline_usage.md`
* `src/fiber_link_sim/schema/README.md`
* `docs/stages_and_flags.md`

## How this differs from OptiCommPy

OptiCommPy provides the underlying physics and DSP building blocks. This repo layers on:

* **A stable contract** (`SimulationSpec → SimulationResult`) for external orchestration tools.
* **Deterministic, pipeline-based composition** so stages can be swapped without changing the spec.
* **Cross-stage metadata, provenance, and artifacts** to make runs reproducible and traceable.

In short: OptiCommPy is the physics toolkit; this repo is the deterministic, versioned simulator
core that wires those blocks into a repeatable end-to-end link model.

## Quick start (developer)

```bash
python -m pip install -e ".[dev]"
```

Run a simulation in your own tooling by importing `simulate()` and passing a spec dict or path.
See `src/fiber_link_sim/schema/examples/` for canonical spec examples.

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

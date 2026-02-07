# AGENTS

## Scope
This file applies to the entire repository unless a more specific `AGENTS.md` exists in a subdirectory.

This repository is the **physics-core** for a fiber-optic communication link simulator. It exposes a stable, versioned `SimulationSpec -> SimulationResult` contract (JSON Schema + Pydantic), and runs the link as a modular phys-pipeline stage chain. An external MCP/UI repo may orchestrate runs and optimization, but **this repo owns the physics truth**.

## Operating principles
- **OptiCommPy-first implementation:** Use OptiCommPy as the primary implementation source for *every* block in the chain (TX, channel/fiber, RX front-end, DSP, FEC, metrics), wherever OptiCommPy provides an equivalent capability. Prefer calling OptiCommPy over reimplementing physics.
- **Modular substitution:** Keep each major block behind a small internal interface so methods can be swapped (e.g., different propagation models, different equalizers) without changing the spec shape.
- **Strict contracts:** `SimulationSpec` and `SimulationResult` are public API. Keep them stable and versioned. Any breaking change requires a spec version bump and an ADR.
- **Deterministic reproducibility:** Same spec + same seed must produce the same results (within defined float tolerances). No hidden randomness.

## Key references (must read first)
- `docs/physics_context.md` — physics intent and block mapping.
- `docs/phys_pipeline_usage.md` — phys-pipeline integration patterns (metrics vs artifacts, State, determinism).
- `src/fiber_physics/schema/README.md` — meaning of all spec flags + rationale + boundaries.
- `src/fiber_physics/schema/simulation_spec.schema.v0.1.json` — input contract.
- `src/fiber_physics/schema/simulation_result.schema.v0.1.json` — output contract.
- `src/fiber_physics/schema/examples/*.json` — canonical example specs.

## End-goal acceptance criteria
Work iteratively across sessions until **all** of the following are true:
1) `simulate()` accepts a spec dict/path, validates it via Pydantic, and produces a `SimulationResult` that validates against the result model.
2) The full chain supports:
   - coherent QPSK long-haul multi-span (primary)
   - IM/DD OOK baseline (regression / sanity)
   - IM/DD PAM4 baseline (datacenter-style sanity)
3) The implementation is staged through phys-pipeline (Tx → Channel → Rx → DSP → FEC → Metrics), with clear modular boundaries.
4) The system is reproducible (deterministic seeding), and has system-wide QA via tests (unit, integration, regression).
5) Documentation is maintained:
   - ADRs for major design decisions and validation strategy
   - schemas/examples/docs kept consistent with code behavior

If an OptiCommPy capability is missing or incompatible for a required feature, implement a minimal fallback behind a backend interface, document the gap and rationale in an ADR, and keep the spec stable.

## Repository boundaries and responsibilities
This repo owns:
- physics + signal processing implementation (via OptiCommPy where possible)
- schemas + Pydantic models
- determinism, metrics definitions, latency model
- artifacts generation (plots/waveforms) behind output flags
- tests + QA

External MCP/UI owns:
- job orchestration, routing UI, optimization scheduling, presentation
- selecting parameter sweeps and calling `simulate()`

Do not move physics logic into MCP/UI. MCP/UI should not compute link metrics itself.

## Architecture: stage chain
Implement simulation as a SequentialPipeline of stages. Recommended stages (names may differ):
- `TxStage` — bits/symbols/waveform generation per format
- `ChannelStage` — fiber propagation (dispersion/nonlinearity), span loss, amplifier behavior, ASE/noise
- `RxFrontEndStage` — coherent receiver or IM/DD receiver front-end
- `DSPStage` — apply configured DSP blocks in order
- `FECStage` — apply configured FEC (if enabled)
- `MetricsStage` — BER/FER, throughput, OSNR/ESNR proxies, and latency breakdown

### OptiCommPy integration
Create an internal adapter module (e.g., `fiber_physics/backends/opticommpy/`) that:
- wraps OptiCommPy function calls
- normalizes units and conventions
- converts OptiCommPy outputs into repo-internal representations
- isolates OptiCommPy API changes from the rest of the codebase

Avoid scattering raw OptiCommPy calls across many files.

## State model (stable shape)
Use **one stable State type** throughout all stages. Populate it progressively rather than changing its structure.

Recommended sections:
- `meta`: run id, seed, spec hash, version, timestamps
- `refs`: references/handles to large arrays/blobs/artifacts (preferred)
- `signals`: current working signal representations (often refs)
- `rx`: decisions/LLRs/constellation refs
- `stats`: small scalars needed for downstream computations

### Large arrays policy
Prefer passing **references** (file paths, artifact refs, blob keys) over embedding huge arrays in State. Keep State hashable and stable for caching and reproducibility.

## Determinism / RNG rules
- All randomness is derived from `runtime.seed`.
- Use a single root RNG stream and deterministically derive per-stage RNGs (or pass an RNG object through State).
- Tests must confirm repeatability of key summary outputs.

## Tests (required) — include PoC unit tests for decisions
Maintain tests at multiple layers:

### Contract tests
- Validate all example specs against the Pydantic spec model.
- Validate all produced results against the Pydantic result model.

### Integration tests
- Run end-to-end simulation for each canonical example spec and assert:
  - `status == "success"`
  - required summary fields exist and are finite
  - error metrics are within valid bounds
  - no unexpected warnings/errors

### Determinism tests
- Same spec+seed => same key summary outputs (exact for discrete values, tolerant for floats).

### Proof-of-concept unit tests (for decisions)
Whenever you choose or change a design (e.g., latency model definition, amplifier auto-gain policy, DSP block defaults, OptiCommPy adapter conventions), add a small unit test that locks the expected behavior. This is how decisions stay stable as the system evolves.

Keep tests small and fast. Use reduced symbol counts and coarse settings where appropriate.

## Documentation via ADRs (required)
Use ADR templates in `docs/adr/` for decisions such as:
- State layout + array/reference policy
- OptiCommPy adapter design and unit conventions
- Propagation/amplifier modeling choices
- DSP chain defaults and parameter validation policy
- Latency model: what is included/excluded and why
- Testing strategy: what is tested and how

Each ADR should also state how the decision is validated (unit/integration tests).

If there is tooling such as `scripts/adr_tools.py`, use it; otherwise create ADRs manually and update any index files used.

## Developer workflow (CI must stay green)
Before opening/submitting any PR, ensure **all CI gates pass locally** (or via the repo’s CI runner):

### Checklist reference
- `docs/ci_checklist.md` — required CI commands and minimal fast checks for local iteration.

### Required checks (must pass)
- **Pre-commit / linting & formatting**
  - `python -m pre_commit run -a`
- **Type checking**
  - `python -m mypy src`
- **Tests**
  - `python -m pytest -q -m "not slow" --durations=10`

### Rules
- Do not submit a PR that fails any of the above checks.
- If a change causes failures, fix them in the same branch/PR (do not leave the repo in a broken state).
- Prefer the smallest change that makes CI green again; document any non-trivial fix in an ADR or PR notes when appropriate.
- Always keep schemas/examples/docs synchronized with code behavior.
- Update `STATUS.md` whenever behavior, tests, or schemas change.

### Setup (preferred)
- Install dev deps: `python -m pip install -e ".[dev]"`
- Run the full CI-equivalent suite with the three commands above.

### Pytest usage (fast vs. slow)
- Fast tests (default): `pytest -m "not slow" --durations=10`
- Slow tests only: `pytest -m slow --durations=10`
- Full suite: `pytest -m "slow or not slow" --durations=10`

## Guardrails
- Favor readability and correctness over premature optimization.
- Keep external dependencies minimal beyond OptiCommPy and standard scientific Python.
- Do not silently ignore invalid spec combinations; validate and return structured errors.
- Never change the public spec/result shape without versioning + ADR + test updates.

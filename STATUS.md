# Project Status (fiber-link-sim)

> **Source of truth:** Update this file whenever behavior, tests, or schemas change.

## Last updated
- Date: 2026-02-08
- By: @openai-codex
- Scope: Implemented phys-pipeline readiness Phases 1-3 (ref-based State, artifact store, RNG isolation)

---

## CI health checklist

| Check | Command | Status | Last run | Notes |
| --- | --- | --- | --- | --- |
| Pre-commit (lint/format) | `python -m pre_commit run -a` | ✅ | 2026-02-08 | Warning about deprecated default_stages. |
| Type checking (mypy) | `python -m mypy src` | ✅ | 2026-02-08 |  |
| Pytest fast | `python -m pytest -q -m "not slow" --durations=10` | ✅ | 2026-02-08 |  |
| Pytest slow | `python -m pytest -q -m slow --durations=10` | ✅ | 2026-02-08 | OptiCommPy runtime warnings observed. |

---

## Test suites (definitions, runtimes, slowest tests)

| Suite | Definition | Typical runtime | Slowest tests (top 3) | Last measured | Notes |
| --- | --- | --- | --- | --- | --- |
| Fast | `-m "not slow" --durations=10` | ~11s | DSP demap, ADC quantization | 2026-02-08 |  |
| Slow | `-m slow --durations=10` | ~6m | QPSK effects toggle, contracts | 2026-02-08 |  |
| Full | `-m "slow or not slow" --durations=10` | TBD | TBD | YYYY-MM-DD |  |

---

## Contract status (spec/result)

### Schema versions
- SimulationSpec schema: `simulation_spec.schema.v0.2.json`
- SimulationResult schema: `simulation_result.schema.v0.1.json`

### Example specs (contract validation + runtime)

| Example | Spec validate | Runtime validate | Notes |
| --- | --- | --- | --- |
| `src/fiber_link_sim/schema/examples/qpsk_longhaul_1span.json` | ✅ | ✅ | Verified 2026-02-07. |
| `src/fiber_link_sim/schema/examples/qpsk_longhaul_manakov.json` | ✅ | ✅ | Verified 2026-02-07. |
| `src/fiber_link_sim/schema/examples/qpsk_longhaul_multispan.json` | ✅ | ✅ | Verified 2026-02-07. |
| `src/fiber_link_sim/schema/examples/ook_smoke.json` | ✅ | ✅ | Verified 2026-02-07. |
| `src/fiber_link_sim/schema/examples/pam4_shorthaul.json` | ✅ | ✅ | Verified 2026-02-07. |

---

## Roadmap checklist

### Stages
- [x] TxStage parity (OptiCommPy-first, format coverage)
- [x] ChannelStage parity (fiber propagation, span loss, amplifier behavior)
- [x] RxFrontEndStage parity (coherent + IM/DD front-ends)
- [x] DSPStage parity (CD compensation, EQ, CPR, timing)
- [x] FECStage parity (optional decode, throughput accounting)
- [x] MetricsStage parity (BER/FER, OSNR/ESNR proxies, latency)

### OptiCommPy adapter
- [x] Central adapter module with normalized units
- [x] Adapter unit tests for each call path
- [x] Documented fallbacks (with ADRs)

### QA / determinism
- [x] Determinism tests (same spec + seed)
- [x] Contract tests (examples validate against models)
- [x] Integration tests (end-to-end, per example)

### Docs / ADRs
- [x] ADRs for adapter conventions + unit normalization
- [x] ADRs for latency model + metrics definitions
- [x] Docs synchronized with schema and behavior

---

## Known issues

- None tracked yet.

## Next actions

- [x] Populate CI and test runtime data after next green run.
- [x] Record example spec pass/fail results from contract tests.
- [x] Execute phys-pipeline readiness roadmap (docs/roadmaps/phys_pipeline_readiness.md) through Phase 3.
- [ ] Integrate phys-pipeline caching backend + scheduled executor once available.

# Project Status (fiber-link-sim)

> **Source of truth:** Update this file whenever behavior, tests, or schemas change.

## Last updated
- Date: YYYY-MM-DD
- By: @your-handle
- Scope: (docs/behavior/tests/schemas/infra)

---

## CI health checklist

| Check | Command | Status | Last run | Notes |
| --- | --- | --- | --- | --- |
| Pre-commit (lint/format) | `python -m pre_commit run -a` | ☐ | YYYY-MM-DD |  |
| Type checking (mypy) | `python -m mypy src` | ☐ | YYYY-MM-DD |  |
| Pytest fast + coverage | `python -m pytest -q -m "not slow" --durations=10 --cov=fiber_link_sim --cov-report=term-missing:skip-covered` | ☐ | YYYY-MM-DD |  |
| Pytest slow | `python -m pytest -q -m slow --durations=10` | ☐ | YYYY-MM-DD |  |

---

## Test suites (definitions, runtimes, slowest tests)

| Suite | Definition | Typical runtime | Slowest tests (top 3) | Last measured | Notes |
| --- | --- | --- | --- | --- | --- |
| Fast | `-m "not slow" --durations=10` | TBD | TBD | YYYY-MM-DD |  |
| Slow | `-m slow --durations=10` | TBD | TBD | YYYY-MM-DD |  |
| Full | `-m "slow or not slow" --durations=10` | TBD | TBD | YYYY-MM-DD |  |

---

## Contract status (spec/result)

### Schema versions
- SimulationSpec schema: `simulation_spec.schema.v0.1.json`
- SimulationResult schema: `simulation_result.schema.v0.1.json`

### Example specs (contract validation + runtime)

| Example | Spec validate | Runtime validate | Notes |
| --- | --- | --- | --- |
| `src/fiber_link_sim/schema/examples/qpsk_longhaul_1span.json` | ☐ | ☐ |  |
| `src/fiber_link_sim/schema/examples/qpsk_longhaul_manakov.json` | ☐ | ☐ |  |
| `src/fiber_link_sim/schema/examples/qpsk_longhaul_multispan.json` | ☐ | ☐ |  |
| `src/fiber_link_sim/schema/examples/ook_smoke.json` | ☐ | ☐ |  |
| `src/fiber_link_sim/schema/examples/pam4_shorthaul.json` | ☐ | ☐ |  |

---

## Roadmap checklist

### Stages
- [ ] TxStage parity (OptiCommPy-first, format coverage)
- [ ] ChannelStage parity (fiber propagation, span loss, amplifier behavior)
- [ ] RxFrontEndStage parity (coherent + IM/DD front-ends)
- [ ] DSPStage parity (CD compensation, EQ, CPR, timing)
- [ ] FECStage parity (optional decode, throughput accounting)
- [ ] MetricsStage parity (BER/FER, OSNR/ESNR proxies, latency)

### OptiCommPy adapter
- [ ] Central adapter module with normalized units
- [ ] Adapter unit tests for each call path
- [ ] Documented fallbacks (with ADRs)

### QA / determinism
- [ ] Determinism tests (same spec + seed)
- [ ] Contract tests (examples validate against models)
- [ ] Integration tests (end-to-end, per example)

### Docs / ADRs
- [ ] ADRs for adapter conventions + unit normalization
- [ ] ADRs for latency model + metrics definitions
- [ ] Docs synchronized with schema and behavior

---

## Known issues

- None tracked yet.

## Next actions

- [ ] Populate CI and test runtime data after next green run.
- [ ] Record example spec pass/fail results from contract tests.

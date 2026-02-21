# Project Status (fiber-link-sim)

> **Source of truth:** Update this file whenever behavior, tests, or schemas change.

## Last updated
- Date: 2026-02-20
- By: @openai-codex
- Scope: Resolved QPSK roadmap contract gaps with vNext schema decisions, latency assumptions, decision-locking tests, and ADR updates.

---

## CI health checklist

| Check | Command | Status | Last run | Notes |
| --- | --- | --- | --- | --- |
| Pre-commit (lint/format) | `python -m pre_commit run -a` | ✅ | 2026-02-20 | Warning about deprecated `default_stages` names (migration pending in `.pre-commit-config.yaml`). |
| Type checking (mypy) | `python -m mypy src` | ✅ | 2026-02-20 | Success: no issues found in 26 source files. |
| Pytest fast (required gate) | `python -m pytest -q -m "not slow" --durations=10` | ✅ | 2026-02-20 | 44 passed, 12 deselected, 1 warning; completed in 124.45s. |
| Pytest slow (supplemental) | `python -m pytest -q -m slow --durations=10` | ✅ | 2026-02-13 | 12 passed, 37 deselected, 13 warnings; completed in 380.24s test time. |

---

## Test suites (definitions, runtimes, slowest tests)

| Suite | Definition | Typical runtime | Slowest tests (top 3) | Last measured | Notes |
| --- | --- | --- | --- | --- | --- |
| Fast | `-m "not slow" --durations=10 --cov=fiber_link_sim --cov-report=term-missing:skip-covered` | ~2m04s (123.80s test time / 128.14s wall) | `test_qpsk_story_manifest_structure`, `test_sim_version_matches_package_release_version`, `test_demap_outputs_hard_bits_and_llrs` | 2026-02-13 | Includes required coverage reporting gate. |
| Slow | `-m slow --durations=10` | ~6m20s (380.24s test time / 383.95s wall) | `test_qpsk_longhaul_effects_toggle_impact`, `test_simulation_results_validate`, `test_adc_bit_depth_impacts_metrics` | 2026-02-13 | OptiCommPy runtime warnings present but non-fatal. |
| Full | `-m "slow or not slow" --durations=10` | ~12m29s (749.06s test time / 752.73s wall) | `test_simulation_results_validate`, `test_simulation_determinism[qpsk_longhaul_manakov.json]`, `test_qpsk_longhaul_effects_toggle_impact` | 2026-02-13 | 49 passed with 24 runtime warnings from OptiCommPy/numpy paths. |

---

## Contract status (spec/result)

### Schema versions
- SimulationSpec schema: `simulation_spec.schema.v0.3.json`
- SimulationResult schema: `simulation_result.schema.v0.3.json`

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
- [x] Integrate phys-pipeline caching backend + scheduled executor once available.

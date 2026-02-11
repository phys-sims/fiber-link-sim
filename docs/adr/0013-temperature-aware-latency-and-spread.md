**Title:** Add temperature-aware propagation latency and deterministic spread metadata

- **Status:** Accepted
- **Date:** 2026-02-10
- **Deciders:** fiber-link-sim maintainers
- **Tags:** latency, environment, determinism, hft
- **Related:** ADR-0009, ADR-0012

## Context

The wrapper platform targets route design workflows where latency sensitivity is primary. Existing latency
budget logic used a constant `fiber.n_group` and did not consume `path.segments[].temp_c`, limiting realism
for environment-sensitive route analysis.

## Decision

1. When `propagation.effects.env_effects=true`, compute propagation latency using per-segment temperatures and
   a linear group-delay coefficient around a fixed reference temperature.
2. Emit deterministic propagation spread metadata (`p05`, `p50`, `p95`, `std`) in
   `summary.latency_metadata.inputs_used.propagation_spread_s` using a seed-derived Monte Carlo.
3. Keep public spec/result schema versions unchanged (v0.2), because fields already exist and this is a
   behavioral enhancement behind existing flags.

## Consequences

- **Pros:** Better route-level latency realism for HFT demos; deterministic statistical signal for optimization.
- **Cons:** Adds assumptions (temperature coefficient + spread sigma) that should be calibrated over time.
- **Risk mitigation:** assumptions are surfaced in `latency_metadata.defaults_used` and covered by tests.

## Validation strategy

- Unit tests verify temperature monotonicity and deterministic spread under fixed seed.
- Analytic tests verify route-length propagation baselines for representative HFT route lengths.

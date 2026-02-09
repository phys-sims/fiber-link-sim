# Version 1 Release Roadmap (Latency, QPSK Visual Story, Validation)

**Executive summary:** This roadmap defines the **Version 1 release** work needed to close three product-critical
gaps: (1) a physically meaningful latency budget in `SimulationResult`, (2) a deterministic, stage-by-stage QPSK
visual story with artifacts at every stage, and (3) a crisp validation narrative with README updates tied to tests.
Work is sequenced into small, shippable PRs that keep CI green and respect the staged pipeline architecture and
stable SimulationSpec → SimulationResult contract.

**Prerequisite roadmaps (must be complete before Version 1 release):**
- `docs/roadmaps/phys_pipeline_readiness.md` — caching + scheduling readiness and artifact/ref policies.
- `docs/roadmaps/qpsk_longhaul.md` — QPSK long-haul stage capability mapping and acceptance criteria.

---

## A) Prioritized milestones (Version 1 release)

### M0 — Roadmap alignment & guardrails (docs-only)
**Goal:** Align on scope, terminology, and acceptance criteria before code changes.

**Acceptance criteria**
- Roadmap published in `docs/roadmaps/version_1_release.md` with milestones, PR plan, latency definitions, QPSK demo,
  and validation plan.
- No spec or behavior changes.

### M1 — LatencyBudget model + contract extension (minimal, backward-compatible)
**Goal:** Replace heuristic latency output with a modeled, decomposed latency budget and encode assumptions.

**Acceptance criteria**
- `SimulationResult.summary.latency_s` becomes a structured `LatencyBudget` with named terms.
- Results include `latency_metadata` detailing assumptions and derivation inputs.
- Any contract additions are versioned and validated (schema + Pydantic + tests).

### M2 — QPSK “wow factor” artifacts pipeline (deterministic stage-by-stage story)
**Goal:** Provide a deterministic artifact suite and an executable script that generates a complete stage narrative.

**Acceptance criteria**
- One command generates deterministic artifacts for every stage of QPSK long-haul.
- Outputs are stored under `docs/assets/qpsk_story/<run_id>/` with a JSON manifest.
- README embeds representative plots (constellation, spectrum, eye, phase error).

### M3 — Validation narrative + README improvements backed by tests
**Goal:** Establish a rigorous validation story with analytic baselines, regression coverage, and documentation.

**Acceptance criteria**
- ≥2 analytic baseline tests (fast) + ≥1 regression/golden test (fast or slow).
- README explains validation approach and links to tests + artifacts.
- STATUS updated after behavior/test/schema changes.

---

## B) Milestone details: files, additions, and test strategy

### M0 — Roadmap alignment & guardrails
**Likely files to change**
- `docs/roadmaps/version_1_release.md` (new)

**New files**
- `docs/roadmaps/version_1_release.md`

**Test strategy**
- None (docs-only).

### M1 — LatencyBudget model + contract extension
**Likely files/modules to change**
- `src/fiber_link_sim/data_models/spec_models.py` (spec model updates; add minimal latency inputs if needed).
- `src/fiber_link_sim/data_models/result_models.py` (add `LatencyBudget` model + metadata).
- `src/fiber_link_sim/schema/simulation_spec.schema.v0.2.json` (add optional latency inputs).
- `src/fiber_link_sim/schema/simulation_result.schema.v0.2.json` (structured latency budget output).
- `src/fiber_link_sim/stages/core.py` (compute latency budget from spec + pipeline state).
- `src/fiber_link_sim/schema/README.md` (document fields & assumptions).
- `docs/adr/` (ADR for latency budget definition and assumptions).
- `STATUS.md` (update after schema/behavior changes).

**New files to add**
- `docs/adr/NNNN-latency-budget-model.md` (ADR template).
- `tests/unit/test_latency_budget.py` (decision-level unit tests).

**Test strategy**
- **Contract tests:** validate updated example specs and result schema compliance.
- **Determinism tests:** same spec+seed yields identical latency budget.
- **Unit tests (PoC):** latency term derivations (propagation, serialization, DSP, FEC).
- Mark heavy end-to-end latency tests as `slow` only if needed.

### M2 — QPSK “wow factor” artifacts pipeline
**Likely files/modules to change**
- `scripts/generate_qpsk_story.py` (new driver script).
- `src/fiber_link_sim/stages/artifacts.py` or `src/fiber_link_sim/artifacts/` (ensure per-stage artifact capture).
- `docs/assets/qpsk_story/` (artifact outputs + manifest).
- `README.md` (embed artifacts + usage).
- `docs/waveform_examples.md` (optional expansion for story narrative).

**New files to add**
- `scripts/generate_qpsk_story.py` (CLI entrypoint).
- `docs/assets/qpsk_story/<run_id>/manifest.json` (generated).
- `docs/assets/qpsk_story/<run_id>/*.svg` (generated plots, local).
- `docs/assets/qpsk_story_public/<run_id>/*.png` (optional publish-ready plots).

**Test strategy**
- **Fast integration test:** run the script on reduced symbols (e.g., `n_symbols=2k`) and assert manifest structure
  + artifact file existence.
- **Determinism test:** same spec+seed results in identical artifact checksums (fast, small sample size).
- Mark full-resolution story generation as `slow` if needed.

### M3 — Validation narrative + README improvements backed by tests
**Likely files/modules to change**
- `tests/analytic/test_awgn_qpsk_ber.py` (analytic BER baseline).
- `tests/analytic/test_latency_propagation.py` (propagation latency baseline).
- `tests/regression/test_qpsk_story_manifest.py` (golden manifest regression).
- `README.md` (validation section + links).
- `docs/refs/physics_context.md` or `docs/stages_and_flags.md` (brief validation summary, optional).
- `STATUS.md` (update after tests/docs changes).

**New files to add**
- `tests/analytic/` (new folder for analytic baselines, if not present).
- `tests/regression/` (new folder for golden tests, if not present).

**Test strategy**
- **Analytic baseline 1 (fast):** QPSK BER vs. SNR in AWGN mode (compare to closed-form curve within tolerance).
- **Analytic baseline 2 (fast):** Propagation latency = `sum(length_m) * n_group / c`.
- **Regression/golden (fast):** QPSK story manifest content + summary metrics hash.
- **Optional cross-tool comparison (slow):** compare OptiCommPy example vs. sim output for a fixed spec.

---

## C) PR plan (small, shippable PRs)

### PR1 — Add Version 1 release roadmap (M0)
**Changes**
- Add `docs/roadmaps/version_1_release.md` with milestones, latency definitions, QPSK demo, and validation plan.

**Done means**
- CI green (`pre-commit`, `mypy`, `pytest -m "not slow"`).
- Roadmap reviewed for alignment with STATUS and architecture constraints.

### PR2 — LatencyBudget contract + derivation (M1)
**Changes**
- Add `LatencyBudget` model + schema updates.
- Implement latency term derivation in Metrics stage.
- Add ADR documenting assumptions and derivations.

**Done means**
- Spec + result schema validated by tests.
- New latency unit tests pass and determinism preserved.
- STATUS updated.

### PR3 — QPSK story generator + artifacts (M2)
**Changes**
- Add `scripts/generate_qpsk_story.py` + artifact manifest.
- Ensure artifacts captured after each stage.
- README embeds a subset of generated plots.

**Done means**
- Script generates all artifacts and manifest in one command.
- Determinism test passes (artifact hashes stable under fixed seed).
- CI green.

### PR4 — Validation tests + README improvements (M3)
**Changes**
- Add analytic baseline tests + regression test.
- Update README with validation story, test commands, and artifact references.

**Done means**
- New tests pass; documentation reflects validations.
- STATUS updated with test runtimes.
- CI green.

---

## D) Latency definitions (proposed LatencyBudget model)

### LatencyBudget decomposition
`LatencyBudget` should be an explicit, structured output in `SimulationResult.summary.latency_s`:

- **propagation_s**: physical propagation delay through fiber
- **serialization_s**: time to serialize payload (and/or framed bits) into symbols
- **dsp_group_delay_s**: delay from digital filters (e.g., RRC, CD compensation, equalizers)
- **fec_block_s**: FEC coding/decoding block latency (frame/block-based)
- **queueing_s** *(optional)*: reserved for future buffering/queue models
- **processing_s**: explicit compute/processing floor (if retained)
- **total_s**: sum of components (explicitly computed, not inferred)

### Derivation from spec fields (minimum viable)

**1) Propagation latency**
- Formula: `propagation_s = sum(path.segments[].length_m) * fiber.n_group / c`
- Inputs: `path.segments[].length_m`, `fiber.n_group`
- Assumptions: uniform group index, ignore temperature dependence unless `path.segments[].temp_c` specifies a model.

**2) Serialization latency**
- Formula: `serialization_s = payload_bits / (signal.symbol_rate_baud * bits_per_symbol * signal.n_pol)`
- Inputs (existing): `signal.format`, `signal.symbol_rate_baud`, `signal.n_pol`, `signal.frame.payload_bits`
- **Minimal extension (if needed):** add `signal.frame.payload_bits` (if not already present) or
  `latency_model.payload_bits_override` to avoid requiring framing changes.
- Assumptions: full utilization (no framing overhead unless `frame` fields specified).

**3) DSP group delay**
- Formula: sum of per-filter group delays derived from DSP chain params.
  - RRC: `rrc_taps / 2 / sample_rate`
  - FFE/MIMO EQ: `eq_taps / 2 / sample_rate`
  - CD compensation FIR: `cd_taps / 2 / sample_rate`
- Inputs: `processing.dsp_chain[].params`, `transceiver.rx.adc.sample_rate_hz` (or `runtime.samples_per_symbol` + symbol rate)
- Assumptions: linear-phase filters; if algorithm does not expose tap count, use conservative defaults documented in metadata.

**4) FEC block latency**
- Formula: `fec_block_s = (fec_block_bits / net_bit_rate)`
- Inputs: `processing.fec.enabled`, `processing.fec.code_rate`, `processing.fec.params` (block size), `signal.*`
- **Minimal extension (if needed):** add `processing.fec.block_size_bits` or infer from LDPC `H` matrix.
- Assumptions: latency counted as 1 block delay; decoding time not included (not runtime).

**5) Processing floor**
- If existing `latency_model.processing_floor_s` stays, it becomes **processing_s** and is distinct from DSP group delay.
- Inputs: `latency_model.processing_floor_s`.
- Assumptions: represents fixed hardware pipeline delay (not CPU runtime).

### Required metadata in results
Add `summary.latency_metadata` (or `summary.latency_s.metadata`) with:
- `assumptions`: list of string assumptions used (e.g., “linear-phase filters”, “no framing overhead”).
- `inputs_used`: key spec fields used in calculations.
- `defaults_used`: which defaults were applied (and values) when params were missing.
- `schema_version`: spec/result version used for latency derivation.

---

## E) QPSK demo deliverable (artifacts + script)

### One-command generator
- **Command:** `python scripts/generate_qpsk_story.py --spec src/fiber_link_sim/schema/examples/qpsk_longhaul_multispan.json`
- **Outputs:** `docs/assets/qpsk_story/<run_id>/` containing plots + `manifest.json`.

### Required plots & JSON summaries per stage
- **TxStage**: waveform PSD, constellation (pre-launch), framing summary JSON.
- **ChannelStage**: post-span spectrum (per span), OSNR vs span plot, received field PSD.
- **RxFrontEndStage**: eye diagram, I/Q time trace, ADC histogram.
- **DSPStage**: constellation before/after CPR, phase error trace, EVM summary.
- **FECStage**: pre/post-FEC BER bar chart, decode iterations summary.
- **MetricsStage**: latency budget table (JSON + plot), throughput summary.

### Output locations & README embedding
- Assets stored in `docs/assets/qpsk_story/<run_id>/` with a stable `latest/` symlink or copy.
- README embeds selected images (constellation, spectrum, latency budget) and links to the manifest.

---

## F) Validation plan

### Analytic baselines (fast)
1. **AWGN QPSK BER baseline**
   - Disable dispersion/nonlinearity/ASE; add controlled AWGN.
   - Compare simulated BER to analytic QPSK BER curve within tolerance.
2. **Propagation latency baseline**
   - Single-span fiber with known length and `n_group`.
   - Assert propagation latency exactly matches formula.

### Regression / golden test (fast or slow)
- **QPSK story manifest regression**: fixed spec+seed generates a manifest hash and key summary metrics that must match.
  (Small symbol count for speed; mark as fast unless artifact generation is too heavy.)

### Optional cross-tool comparison (slow)
- Compare metrics (BER/EVM/OSNR) from OptiCommPy example notebooks vs. this pipeline for a fixed spec;
  document deltas and expected tolerances in a short doc/test note.

---

## Notes on minimal contract extension (if needed)

To support the latency budget without breaking existing specs, prefer **optional** additions:
- `latency_model.payload_bits_override` (optional) for serialization latency if framing fields are absent.
- `processing.fec.block_size_bits` (optional) for FEC block latency if the decoder doesn’t expose block size.

These additions must be versioned, documented in `schema/README.md`, validated by Pydantic models, and
covered by unit tests.

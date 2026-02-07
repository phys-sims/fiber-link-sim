# OptiCommPy adapter notes (for `phys-pipeline` stages)

This document is the **single source of truth** for how our simulator maps the project’s **schema** (SimulationSpec/SimulationResult) onto **OptiCommPy** calls, and how those calls are decomposed into **phys-pipeline stages**.

The goal is to keep OptiCommPy usage **behind a thin adapter layer**, so that:
- the external JSON schema stays stable,
- we can swap OptiCommPy versions (or even other simulators later) with minimal blast radius,
- tests can validate “schema → OptiCommPy → results” end-to-end.

OptiCommPy is under active development, so **expect API/behavior drift** across releases. Treat the adapter as a compatibility boundary. citeturn17search7turn19search7

---

## 0) What OptiCommPy provides (capability map)

OptiCommPy is organized into three big groups—**comm**, **dsp**, and **models**—and provides:
- **Transmitters** (e.g., `simpleWDMTx`, `pamTransmitter`) citeturn21view0
- **Channel propagation** (linear fiber, SSFM, Manakov SSFM) citeturn16view1turn16view0turn22view0
- **Coherent receiver front-end** (single-pol and PDM) citeturn15view1turn15view0
- **DSP blocks** (EDC, MIMO equalizer, carrier recovery, clock recovery, DBP) citeturn18search4turn18search0turn18search1turn18search5
- **Metrics** (BER/SER, EVM, MI/GMI, LLR, OSNR evolution) citeturn17search1turn17search0turn17search2turn17search3
- **FEC utilities** (LDPC encoding/decoding and helpers) citeturn20search0

This is sufficient to implement an end-to-end **coherent QPSK long-haul** simulation using **`simpleWDMTx` → `manakovSSF` → `pdmCoherentReceiver` → DSP → metrics/FEC**. citeturn21view0turn22view0turn15view0turn18search4turn20search0

**Important limitation (honesty):** the documented SSFM/Manakov channel models expose **α, D, γ** plus span/amplifier controls. That’s a standard NLSE/Manakov-style physical layer model; it’s not a “full GLNSE kitchen sink” (e.g., higher-order dispersion terms, Raman, self-steepening, etc.) unless OptiCommPy adds those later. Plan any “true GLNSE” upgrade as a future ADR. citeturn16view0turn22view0

---

## 1) Terminology we must keep straight

These words show up in schema, MCP/UI, and OptiCommPy. Don’t mix them.

### 1.1 Scenario (schema-level)
A **scenario** is a self-contained “system configuration” that the UI/MCP requests:
- modulation + rates,
- channel/path/fiber,
- processing/DSP/FEC toggles,
- desired outputs (latency/throughput/BER/etc.).

Think: **one JSON SimulationSpec → one SimulationResult**.

### 1.2 Path segment vs span (physics-level)
- A **path segment** (schema) is a routing leg with a length and optional environmental descriptors (region, temperature zone, etc.).
- A **span** (OptiCommPy) is the repeated structure in long-haul modeling: fiber length `Lspan` with an amplifier (often EDFA) between spans. OptiCommPy channel models explicitly expose `Ltotal` and `Lspan`. citeturn22view0turn16view0

Mapping rule:
- If the route is long-haul and you’re modeling inline amplification, the *effective physics* should be expressed in **spans** (even if the UI thinks in segments).

### 1.3 “Encoding format” vs waveform parameters
In our schema, “encoding format” often means “modulation format.” In fiber comms, **propagation latency** is dominated by **group velocity** and depends on **path length + refractive index**, not whether the symbols are QPSK/PAM4/OOK.

But modulation affects:
- required bandwidth,
- symbol rate for a given net bitrate,
- required DSP/FEC overhead,
- tolerable OSNR/NLIN,
- achievable post-FEC throughput at a given distance.

So: modulation is primarily a **QoT/throughput** lever, not a **speed-of-light latency** lever.

---

## 2) The “adapter boundary”: what must live in our repo

Create an internal module (example layout):

```
src/<pkg>/adapters/opticommpy/
  __init__.py
  versioning.py
  param_builders.py
  tx.py
  channel.py
  rx_frontend.py
  dsp_chain.py
  metrics.py
  fec.py
  types.py
```

Design rules:
1. **No stage imports OptiCommPy directly** except inside this adapter package.
2. All OptiCommPy calls go through small wrapper functions with:
   - strict parameter validation,
   - unit conversions,
   - deterministic seeding,
   - consistent array shapes.
3. Adapter returns **plain python/numpy** objects (fields, symbols, bit arrays) and **metadata** needed for SimulationResult.

Why: OptiCommPy may reorganize modules; the adapter isolates churn. citeturn19search7

---

## 3) `optic.utils.parameters`: the core parameter container

OptiCommPy expects a parameter object in many places (Tx/channel/DSP/FEC). The public docs index lists `parameters` as a class in `optic.utils`. citeturn14search13

**Adapter policy**
- Build parameter objects in `param_builders.py` from our schema models.
- Never pass raw dicts directly into OptiCommPy.
- Record the final parameter object fields (or a sanitized snapshot) into result metadata for reproducibility.

---

## 4) Stage decomposition (phys-pipeline)

Below is a recommended stage chain. It matches the end-to-end OptiCommPy examples structure (Tx → channel → Rx → metrics). citeturn14search3turn14search7

### 4.1 Coherent QPSK long-haul (primary target)

| Stage | Input | Output | OptiCommPy anchor |
|---|---|---|---|
| `BuildScenarioStage` | SimulationSpec | validated, normalized spec (units, defaults) | (ours) |
| `TxStage` | normalized spec | `(sigTx, symbTx, tx_meta)` | `simpleWDMTx(param)` (set `constType='psk', M=4`, `nChannels=1 or >1`) citeturn21view0 |
| `ChannelStage` | `sigTx` + channel params | `sigRxOpt` + channel_meta | `manakovSSF(Ei,param)` for dual-pol long-haul citeturn22view0 |
| `RxFrontendStage` | `sigRxOpt` + LO params | `sigRxElec` | `pdmCoherentReceiver(Es,Elo,paramFE,...)` citeturn15view0 |
| `DSPStage` | `sigRxElec` + dsp params + (optional) `symbTx` | `symbRx` + dsp_meta | `edc`, `mimoAdaptEqualizer`, `viterbi/ddpll/bps`, `gardnerClockRecovery`, etc. citeturn18search4turn18search0turn18search1turn19search3 |
| `MetricsStage` | `symbRx`, `symbTx` | pre-FEC metrics | `fastBERcalc`, `calcEVM`, `calcLLR`, MI/GMI citeturn17search0turn17search2turn17search3 |
| `FECStage` (optional) | LLRs + FEC params | decoded bits + post-FEC metrics | `decodeLDPC`, `encodeLDPC` if simulating the full chain citeturn20search0 |
| `LatencyStage` | path + signal params | latency numbers | (mostly ours; physical + processing model) |

### 4.2 IM-DD OOK (smoke test / debug mode)
Use OptiCommPy’s direct-detection “getting started” style: linear fiber + photodiode + BER/Q calculation. citeturn14search7turn17search6

### 4.3 PAM4 short-reach (data-center flavored)
Use `pamTransmitter` for the transmitter and choose linear fiber (or a simplified channel) first, then incrementally add impairments. `pamTransmitter` exists explicitly for optical PAM signals. citeturn21view0

---

## 5) Mapping schema fields → OptiCommPy parameters

This section is the **meat**: how your schema inputs become OptiCommPy calls.

### 5.1 Path inputs
Schema path model should include:
- total length (or list of segments),
- optional “geo/environment” tags.

**Adapter mapping**
- OptiCommPy channel functions primarily take **fiber length in km**: `Ltotal` / `L` and (for long-haul) `Lspan`. citeturn22view0turn16view1turn16view0
- Therefore, path segmentation is not a first-class concept in OptiCommPy. You have two implementable strategies:

**Strategy A — flatten segments (default, simplest)**
- `Ltotal_km = sum(segment.length_km)`
- choose **one** fiber parameter set for the whole path
- ignore environmental variation initially
- record in metadata: `path_model="flattened"`

**Strategy B — piecewise channel (more accurate, more compute)**
- run `manakovSSF` (or `ssfm`) sequentially per segment with segment-specific parameters
- be careful: each segment should still obey span modeling rules (see §6)
- record: `path_model="piecewise"` and store segment-by-segment params

**Temperature / geo effects**
- If you later model temperature zones, it should not be a random “geo bool.” It should be:
  - either a *derived parameterization* that modifies known physical knobs (e.g., loss, dispersion, refractive index),
  - or a *lookup table* keyed by region tags.
- Put that logic in **our** adapter (`path_effects.py`), not inside MCP/UI.

### 5.2 Fiber inputs
OptiCommPy fiber/channel models (SSFM & Manakov SSF) expose these core parameters:
- `alpha` [dB/km], `D` [ps/nm/km], `gamma` [1/W/km], plus `Ltotal/Lspan/hz`. citeturn16view0turn22view0

**Key note:** our schema should treat these as **physical defaults** and allow overrides per scenario.

#### Recommended mapping for coherent long-haul
Use `manakovSSF` and set:
- `param.Ltotal = total_length_km`
- `param.Lspan = span_length_km`
- `param.hz = step_km`
- `param.alpha = alpha_db_per_km`
- `param.D = D_ps_nm_km`
- `param.gamma = gamma_per_W_km`
- `param.Fc = carrier_frequency_hz`
- `param.Fs = sampling_frequency_hz` (derived from `Rs*SpS`)
- `param.amp = 'edfa' | 'ideal' | 'None'`
- `param.NF = noise_figure_db` (if EDFA)
…and optionally the nonlinear step-size adaptation controls (`nlprMethod`, etc.). citeturn22view0

This directly answers your earlier question “should `needs amplifier` be its own variable?”:
- In OptiCommPy, the amplifier behavior is already controlled by `param.amp` and `param.NF` in the channel model. citeturn22view0turn16view0
- So a separate `needs_amplifier: bool` is redundant *if* your schema exposes `amp_model` (None/ideal/edfa) explicitly.
- If UI wants a simple toggle, MCP can map `needs_amplifier=True` → `amp_model='edfa'` and fill default NF.

### 5.3 Modulation / “encoding format” inputs

#### Coherent QPSK (preferred)
Use `simpleWDMTx(param)` with:
- `param.constType = 'psk'`
- `param.M = 4`
…and set waveform controls:
- `Rs` (baud), `SpS`, `pulseType`, `pulseRollOff`, `nFilterTaps` citeturn21view0

For long-haul realism:
- Use `param.nPolModes = 2` for PDM (dual polarization) when you intend to run Manakov and PDM coherent receiver. citeturn21view0turn22view0turn15view0

#### PAM4
Use `pamTransmitter(param)` and set `param.M=4`. It supports `Rs`, `SpS`, pulse shaping and output power. citeturn21view0

#### OOK
For OOK smoke tests:
- OptiCommPy includes metrics support where `fastBERcalc` accepts `constType='ook'`. citeturn17search0
- The direct-detection example in “Getting started” uses OOK and evaluates BER using `bert(I_Rx)`. citeturn17search6turn14search7

**Latency note:** modulation choice does not change propagation delay; it changes the bitrate that can be sustained at that distance. (§7)

### 5.4 Receiver front-end inputs

For coherent systems, OptiCommPy provides:
- `coherentReceiver` (single-pol) and
- `pdmCoherentReceiver` (dual-pol). citeturn15view1turn15view0

For PDM coherent, `pdmCoherentReceiver` has a rich `paramFE` structure for impairments:
- polarization rotation, PDL, polarization delay,
- per-pol I/Q phase imbalance, amplitude imbalance, and skew. citeturn15view0

**Adapter policy**
- Default to an “ideal” front-end (all imbalances 0) unless the scenario explicitly requests impairment injection.
- Keep these knobs in schema even if MCP doesn’t tune them initially; just mark them “advanced.”

### 5.5 DSP toggles / processing methods
OptiCommPy has a catalog of DSP functions; the DSP docs list major blocks and there are generated pages for key algorithms. citeturn18search4turn18search0turn18search1turn19search3

A recommended coherent DSP chain (with upgrade points) looks like:

1. **Resampling / normalization**
   - Keep `Fs` and `SpS` consistent; normalize power if needed (`pnorm` etc., see DSP core list). citeturn18search4

2. **EDC (chromatic dispersion compensation)**
   - `edc(Ei, param)` where `param.L`, `param.D`, `param.Fc` are required. citeturn19search3

3. **Timing recovery**
   - Use Gardner-based timing recovery (`gardnerTED` + `gardnerClockRecovery`) in the clock recovery module. citeturn18search4turn18search2

4. **MIMO adaptive equalization**
   - `mimoAdaptEqualizer(x, param, dx)` supports multiple algorithms (CMA/RDE/NLMS/RLS/etc.) and takes `SpS`, taps, step size, etc. citeturn18search0

5. **Carrier frequency offset (CFO) and carrier phase recovery (CPR)**
   - `fourthPowerFOE` for CFO estimation, and `viterbi` or `ddpll` (or BPS) for CPR. citeturn18search4turn18search1turn18search7

6. **Optional: Digital backprop (DBP)**
   - `manakovDBP` exists for dual-pol backprop and uses the same `Ltotal/Lspan/hz` style parameters. citeturn18search5

**Adapter implementation pattern**
- Represent the DSP selection in schema as an **ordered list** of blocks.
- Adapter should translate that list into a `dsp_chain.run(...)` function that applies blocks in order, returning:
  - final symbols,
  - intermediate taps/estimates (for debugging/plots),
  - and a compact “recipe fingerprint” to store in results.

**MCP vs physics repo**
- MCP should choose **which recipe** to run (and maybe a few high-level knobs), not implement DSP itself.
- The physics repo owns what “EDC” means in terms of actual implementation calls.

### 5.6 Metrics and post-FEC metrics

OptiCommPy metrics support includes:
- `fastBERcalc(rx, tx, M, constType)` for Monte-Carlo BER/SER citeturn17search0
- `calcEVM` for EVM metrics citeturn17search2
- `calcLLR` for LLRs (needed for soft-decision FEC) citeturn17search3
- OOK-specific `bert(Irx)` used in the getting started example citeturn17search6turn17search1

**Adapter policy**
- Always compute at least one canonical metric set:
  - pre-FEC BER (or Q for OOK),
  - EVM,
  - and if coherent: MI/GMI optional (for “capacity-like” reporting). citeturn17search1

#### FEC (LDPC)
OptiCommPy provides `encodeLDPC(bits,param)` and `decodeLDPC(llrs,param)` plus SPA/MSA decoders and ALIST helpers. citeturn20search0turn20search4turn20search2

**Current v0.1 behavior:** the adapter performs **actual LDPC decode** using `decodeLDPC` when FEC is enabled and the parity-check
matrix is supplied. Soft bits (LLRs) are preferred; hard bits are converted to fixed-magnitude LLRs as a fallback.

**Required `processing.fec.params` payload (LDPC decode):**
- `H`: parity-check matrix (2D list/array, shape `m x n`).
- `max_iter` (or legacy `max_iters`): maximum decoder iterations (int).
- `alg`: decoding algorithm (`"SPA"` or `"MSA"`).
- `prec` (optional): numeric precision (defaults to `np.float32`).

Post-FEC BER/FER are measured directly from decoded bits against the transmitted coded bits for deterministic validation.

---

## 6) Long-haul modeling details (where most bugs will be)

### 6.1 Span and amplification semantics
`ssfm` and `manakovSSF` expose:
- `Ltotal`, `Lspan`, `amp` and `NF` (noise figure) as part of the channel parameter object. citeturn16view0turn22view0

Interpretation:
- The link is modeled as `Ns = Ltotal / Lspan` spans.
- `amp='edfa'` implies adding ASE noise with noise figure `NF` each span.
- `amp='ideal'` means perfect gain with no added noise (useful for isolating nonlinearities).
- `amp='None'` means no amplification (power decays exponentially). citeturn16view0turn22view0

### 6.2 Step size (`hz`) vs correctness vs runtime
`hz` is the SSFM step size in km. Smaller `hz` = higher accuracy, higher compute cost. citeturn16view0turn22view0

Adapter policy:
- Make `hz` an explicit schema field for “realism.”
- Provide a safe default (e.g., 0.5 km per docs default) and allow MCP to dial it coarser for faster previews.

### 6.3 Sampling frequency consistency
Many blocks require `Fs` (sampling frequency) and/or `SpS` (samples per symbol).
- Tx functions specify `Rs` and `SpS` and therefore define `Fs = Rs * SpS` by construction. citeturn21view0
- Channel models require `param.Fs` for correctness. citeturn16view0turn22view0
- Coherent front-end requires `paramFE.Fs`. citeturn15view0turn15view1

Adapter policy:
- Derive `Fs` in one place (Tx param builder).
- Store it in state and reuse everywhere; do not recompute inconsistently.

### 6.4 Polarization shape conventions
OptiCommPy expects “PDM” signals as arrays where polarization multiplexing is represented in the signal structure (docs refer to `(N,2)` for pol-mux fields in some device models like PBS). citeturn13search13turn15view0

Adapter policy:
- Standardize on one internal representation for pol-mux signals:
  - either shape `(N, 2)` complex array,
  - or a dedicated dataclass that wraps `(Ex, Ey)`.
- Write converters at the adapter boundary and unit-test them.

---

## 7) Latency model: what we should and should not claim

The simulator’s “latency” output should be explicit about what it means.

### 7.1 Physical propagation latency
If you only know **distance**, the simplest physical estimate is:
- `t_prop = length / v_g`, where `v_g = c / n_g`

If the schema includes group index `n_g` (or an equivalent), use it. If not, choose a consistent default and document it.

This is not something OptiCommPy computes for you; it’s “bookkeeping” on the path object.

### 7.2 Processing latency
DSP/FEC adds pipeline/algorithmic latency that depends on:
- filter lengths (RRC taps, equalizer taps),
- block sizes and window lengths (e.g., Viterbi averaging window `N`), citeturn18search1
- FEC decoding iterations (`maxIter` in LDPC decode). citeturn20search0

You have three tiers for reporting:
1. **Ignore processing latency** (only propagation; simplest)
2. **Estimate processing latency** using configured tap/window sizes
3. **Benchmark runtime** (wall-clock) and treat it as “compute time,” not network latency

Adapter policy:
- Output both `propagation_latency_s` and `estimated_processing_latency_s`, and clearly label “estimated.”

---

## 8) Testing strategy (how we avoid fooling ourselves)

You need tests at 3 levels.

### 8.1 Adapter unit tests (fast)
- Parameter builders: schema → parameters object fields
- shape converters: pol-mux arrays in/out
- deterministic seeding produces deterministic bit streams (when feasible)

### 8.2 Stage-level tests (medium)
- Tx stage returns expected symbol rate, `Fs`, and signal length relationship
- Channel stage basic sanity (power decreases with `alpha` if `amp=None`, etc.) citeturn16view0turn22view0
- DSP stage can recover constellation on a short link with “easy” settings

### 8.3 End-to-end “golden” tests (slower)
Anchor to OptiCommPy example notebooks:
- OOK getting started: confirm BER/Q are in a plausible range and call the same metric function `bert`. citeturn17search6turn14search7
- Coherent WDM transmission notebook: confirm pipeline runs end-to-end and key stats are plausible. citeturn14search3turn18search6

Do not assert exact floating-point values unless you lock random seeds + numerical precision + version pins.

---

## 9) “Future upgrade” checklist (good ADR prompts)

These are the knobs you’ll likely want later; each should be an ADR when implemented.

### 9.1 Channel physics
- higher-order dispersion / slope (beyond a single `D` value)
- PMD model (random birefringence / DGD)
- Raman gain / distributed amplification
- nonlinear phase noise modeling beyond ASE+NLIN

(OptiCommPy currently documents `D` and `gamma` in SSFM/Manakov but not full higher-order GLNSE terms.) citeturn16view0turn22view0

### 9.2 WDM realism
- `nChannels > 1` with realistic grid spacing `wdmGridSpacing`
- per-channel power optimization
- cross-channel metrics and QoT constraints

The WDM transmitter explicitly exposes `nChannels` and `wdmGridSpacing`. citeturn21view0

### 9.3 DSP + impairments
- add front-end impairments via `pdmCoherentReceiver`’s `paramFE` fields (PDL, skew, imbalance, etc.) citeturn15view0
- DBP / Volterra equalization comparisons citeturn18search4turn18search5
- pilot-aided phase recovery options vs blind methods

### 9.4 FEC and “post-FEC throughput” credibility
- actual LDPC decode for representative code families (DVB-S2, etc.)
- code-rate selection as a function of GMI/OSNR
- matching “overhead” definitions to standard practice

OptiCommPy exposes LDPC encode/decode and algorithm selection (`SPA` vs `MSA`) via parameters. citeturn20search0

---

## 10) Practical implementation notes (avoid common foot-guns)

1. **Don’t leak OptiCommPy objects into schema outputs**. Only output JSON-serializable primitives + arrays (compressed) + metadata.
2. **Pin OptiCommPy version** in `pyproject.toml` and record it in `SimulationResult.meta`.
3. **Keep signal arrays out of default SimulationResult** (too large). Instead store:
   - summary stats,
   - optional artifacts saved to disk (for debug), with paths.
4. **Use numerical precision intentionally**:
   - channel models expose `param.prec` (e.g., `np.complex128`). citeturn16view0turn22view0
   - keep it consistent across stages to avoid “heisenbugs.”

---

## 11) Minimal “starter mappings” (what must be implemented first)

If you implement only these mappings, you’ll have an end-to-end coherent QPSK long-haul simulator:

- Tx: `simpleWDMTx` with `M=4`, `constType='psk'`, `nPolModes=2` citeturn21view0
- Channel: `manakovSSF` with `Ltotal`, `Lspan`, `hz`, `alpha`, `D`, `gamma`, `amp='edfa'`, `NF` citeturn22view0
- Rx front-end: `pdmCoherentReceiver` with `paramFE.Fs` (ideal impairments) citeturn15view0
- DSP: at least EDC + MIMO equalizer + CPR (Viterbi) citeturn19search3turn18search0turn18search1
- Metrics: `fastBERcalc` + `calcEVM` citeturn17search0turn17search2
- Optional post-FEC: `decodeLDPC` driven by `calcLLR` citeturn20search0turn17search3

Everything else can be layered in without breaking schema if you keep the adapter boundary clean.

# Physics Context (Design Blueprint → Implementation Notes)

This repo implements a **modular physics-based simulator for optical fiber communication links** intended to be used as a backend
for a routing/route-planning product (UI + MCP wrapper lives elsewhere). The goal is to simulate end-to-end performance and latency
for candidate fiber routes and system configurations.

## System blocks (conceptual pipeline)

1. **Bit source / framing**
   - Generate payload bits and frame structure (preamble/pilots).
2. **Transmitter**
   - Map bits to symbols (QPSK / OOK / PAM4).
   - Pulse shaping (e.g., RRC) and DAC/drive modeling (optional, controlled by processing/transceiver flags).
   - Laser model (linewidth, phase noise) where relevant.
3. **Optical channel**
   - Fiber propagation (dispersion + nonlinearity via (DP) NLSE/GLNSE family; long-haul uses multi-span).
   - Lumped loss per span and optical amplification (EDFA) with ASE noise.
   - Optional impairments (PMD, environment effects) as explicit toggles.
4. **Receiver front-end**
   - **Coherent** receiver (primary): LO + mixing + balanced detection + ADC.
   - **IM/DD** receiver (secondary / tests): direct detection + ADC.
   - ADC behavior: resample the analog waveform to `transceiver.rx.adc.sample_rate_hz` and apply a uniform
     quantizer with `transceiver.rx.adc.bits` full-scale set by the maximum absolute sample value
     (complex signals quantize real/imag independently).
5. **DSP chain**
   - Resampling / timing recovery (as modeled)
   - Matched filtering
   - CD compensation
   - Equalization (MIMO for coherent DP, FFE for IM/DD)
   - Carrier phase recovery (coherent)
   - Demap to bits or soft LLRs
   - **Default ordering when `processing.dsp_chain` is empty:**
     - **Coherent QPSK:** resample → matched_filter → cd_comp → mimo_eq → cpr → demap
     - **IM/DD (OOK/PAM4):** resample → matched_filter → ffe → demap
6. **FEC**
   - Optional LDPC decode (or none for early smoke tests).
7. **Metrics + latency accounting**
   - Pre-FEC BER, post-FEC BER (or post-FEC target estimate), FER.
   - OSNR/SNR/EVM/Q-factor where available.
   - Latency breakdown: propagation + serialization + processing estimate.

## Primary target mode

- **Coherent QPSK long-haul** multi-span links.
- Propagation model: **Manakov (DP)** in the long-haul baseline spec.
- IM/DD modes (OOK, PAM4) exist mainly as smoke/regression tests and for a datacenter-style short-haul baseline.

## Out of scope initially

- Vendor-grade DSP stacks and hardware-accurate latency micro-modeling.
- Detailed network-layer packetization beyond a generic frame bit-count model.
- Raman amplification, gain flattening filters, ROADM/wavelength routing.
- Full PMD coupling models beyond a coarse toggle.

## Separation from research solver

This project may use the same *class of equations* as research work (GLNSE/DP-NLSE family), but the implementation/backends here are
kept separate and product-oriented (reproducible spec → deterministic result). Do not import or depend on research-only code paths in this repo.

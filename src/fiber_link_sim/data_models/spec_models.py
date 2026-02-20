"""
Pydantic models for SimulationSpec / SimulationResult.

This file is intended to be the *single source of truth* for runtime validation at the
library boundary. JSON Schema files in src/fiber_physics/schema/ should be generated
from (or kept consistent with) these models.

v0.2 focuses on:
- coherent QPSK long-haul (Manakov DP) as the primary target
- IM/DD OOK and PAM4 as smoke/regression and short-haul baselines
- deterministic runs via an explicit seed
"""

from __future__ import annotations

from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

# -----------------------------
# Spec models
# -----------------------------


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Geo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    polyline_wgs84: list[tuple[float, float]] = Field(
        default_factory=list,
        description="Optional [lon, lat] points.",
    )


class PathSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    length_m: float = Field(..., gt=0)
    temp_c: float | None = None
    notes: str | None = None


class Path(BaseModel):
    model_config = ConfigDict(extra="forbid")
    segments: list[PathSegment]
    geo: Geo = Field(default_factory=Geo)


class Fiber(BaseModel):
    model_config = ConfigDict(extra="forbid")
    alpha_db_per_km: float = Field(..., ge=0)
    beta2_s2_per_m: float
    beta3_s3_per_m: float | None = None
    gamma_w_inv_m: float = Field(..., ge=0)
    pmd_ps_sqrt_km: float = Field(0.0, ge=0)
    n_group: float = Field(..., gt=1.0)


AmplifierType = Literal["none", "edfa"]
AmplifierMode = Literal["none", "auto_gain", "fixed_gain"]


class Amplifier(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: AmplifierType
    mode: AmplifierMode
    noise_figure_db: float | None = Field(None, ge=0)
    max_gain_db: float | None = Field(None, ge=0)
    fixed_gain_db: float | None = None

    @model_validator(mode="after")
    def _check_amp(self) -> Amplifier:
        if self.type == "none":
            if self.mode != "none":
                raise ValueError("amplifier.mode must be 'none' when amplifier.type is 'none'")
            if (
                self.noise_figure_db is not None
                or self.max_gain_db is not None
                or self.fixed_gain_db is not None
            ):
                raise ValueError("gain/NF fields must be omitted when amplifier.type is 'none'")
            return self

        # EDFA
        if self.noise_figure_db is None:
            raise ValueError("amplifier.noise_figure_db is required for EDFA")
        if self.mode == "auto_gain" and self.max_gain_db is None:
            raise ValueError("amplifier.max_gain_db is required when amplifier.mode is 'auto_gain'")
        if self.mode == "fixed_gain" and self.fixed_gain_db is None:
            raise ValueError(
                "amplifier.fixed_gain_db is required when amplifier.mode is 'fixed_gain'"
            )
        return self


SpanMode = Literal["from_path_segments", "fixed_span_length"]


class Spans(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: SpanMode
    span_length_m: float = Field(..., gt=0)
    amplifier: Amplifier


SignalFormat = Literal["coherent_qpsk", "imdd_ook", "imdd_pam4"]


class Frame(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payload_bits: int = Field(..., ge=1)
    preamble_bits: int = Field(0, ge=0)
    pilot_bits: int = Field(0, ge=0)


class Signal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: SignalFormat
    symbol_rate_baud: float = Field(..., gt=0)
    rolloff: float = Field(..., ge=0, le=1)
    n_pol: Literal[1, 2]
    frame: Frame


class Tx(BaseModel):
    model_config = ConfigDict(extra="forbid")
    laser_linewidth_hz: float = Field(0.0, ge=0)
    launch_power_dbm: float


class ADC(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sample_rate_hz: float = Field(..., gt=0)
    bits: int = Field(..., ge=1, le=16)


class RxNoise(BaseModel):
    model_config = ConfigDict(extra="forbid")
    thermal: bool = True
    shot: bool = True


class Rx(BaseModel):
    model_config = ConfigDict(extra="forbid")
    coherent: bool
    lo_linewidth_hz: float = Field(0.0, ge=0)
    adc: ADC
    noise: RxNoise = Field(default_factory=RxNoise)


class Transceiver(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tx: Tx
    rx: Rx


DSPBlockName = Literal["resample", "matched_filter", "cd_comp", "mimo_eq", "ffe", "cpr", "demap"]


class DspBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: DSPBlockName
    enabled: bool = True
    params: dict[str, Any] = Field(default_factory=dict)


FecScheme = Literal["none", "ldpc"]


class Fec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    scheme: FecScheme = "ldpc"
    code_rate: float = Field(0.8, ge=0.1, le=1.0)
    params: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_fec(self) -> Fec:
        if not self.enabled:
            if self.scheme != "none":
                raise ValueError("fec.scheme must be 'none' when fec.enabled is false")
            if self.code_rate != 1.0:
                raise ValueError("fec.code_rate must be 1.0 when fec.enabled is false")
        return self


class Autotune(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    budget_trials: int = Field(30, ge=1)
    targets: list[Literal["max_net_after_fec"]] = Field(
        default_factory=lambda: cast(list[Literal["max_net_after_fec"]], ["max_net_after_fec"]),
    )


class Processing(BaseModel):
    model_config = ConfigDict(extra="forbid")
    autotune: Autotune | None = None
    dsp_chain: list[DspBlock] = Field(default_factory=list)
    fec: Fec


PropagationModel = Literal["scalar_glnse", "manakov"]
PropagationBackend = Literal["builtin_ssfm"]


class Effects(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dispersion: bool = True
    nonlinearity: bool = True
    ase: bool = True
    pmd: bool = False
    env_effects: bool = False


class SSFM(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dz_m: float = Field(100.0, gt=0)
    step_adapt: bool = False


class Propagation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: PropagationModel
    backend: PropagationBackend = "builtin_ssfm"
    effects: Effects = Field(default_factory=Effects)
    ssfm: SSFM = Field(default_factory=SSFM)


class Runtime(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seed: int = Field(..., ge=0)
    n_symbols: int = Field(..., ge=128)
    samples_per_symbol: int = Field(..., ge=1, le=64)
    max_runtime_s: float = Field(..., gt=0)


SpreadSamplingPolicy = Literal["normal_mc"]


class PropagationSpreadModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sigma_c: float = Field(1.0, ge=0.0, le=20.0)
    samples: int = Field(512, ge=16, le=50_000)
    sampling_policy: SpreadSamplingPolicy = "normal_mc"


class EnvironmentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal["v1"] = "v1"
    temperature_reference_c: float = Field(20.0, ge=-60.0, le=120.0)
    group_delay_temp_coeff_per_c: float = Field(7e-6, ge=0.0, le=1e-3)
    spread: PropagationSpreadModel = Field(default_factory=lambda: PropagationSpreadModel())


class LatencyModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    serialization_weight: float = Field(..., ge=0)
    processing_weight: float = Field(..., ge=0)
    processing_floor_s: float = Field(..., ge=0)
    queueing: QueueingModel = Field(default_factory=lambda: QueueingModel())
    framing: FramingOverheadModel = Field(default_factory=lambda: FramingOverheadModel())
    hardware_pipeline: HardwarePipelineModel = Field(
        default_factory=lambda: HardwarePipelineModel()
    )
    environment: EnvironmentModel = Field(default_factory=lambda: EnvironmentModel())


class QueueingModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ingress_buffer_s: float = Field(0.0, ge=0)
    egress_buffer_s: float = Field(0.0, ge=0)
    scheduler_tick_s: float = Field(0.0, ge=0)


FramingFecOverheadMode = Literal["none", "auto_from_code_rate", "fixed_ratio"]


class FramingOverheadModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    include_preamble_bits: bool = False
    include_pilot_bits: bool = False
    fec_overhead_mode: FramingFecOverheadMode = "none"
    fec_overhead_ratio: float | None = Field(None, ge=0)

    @model_validator(mode="after")
    def _check_fec_overhead(self) -> FramingOverheadModel:
        if self.fec_overhead_mode == "fixed_ratio" and self.fec_overhead_ratio is None:
            raise ValueError("framing.fec_overhead_ratio is required when mode is 'fixed_ratio'")
        if self.fec_overhead_mode != "fixed_ratio" and self.fec_overhead_ratio is not None:
            raise ValueError("framing.fec_overhead_ratio is only valid when mode is 'fixed_ratio'")
        return self


class HardwarePipelineModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tx_fixed_s: float = Field(0.0, ge=0)
    rx_fixed_s: float = Field(0.0, ge=0)
    dsp_fixed_s: float = Field(0.0, ge=0)
    fec_fixed_s: float = Field(0.0, ge=0)


ArtifactLevel = Literal["none", "basic", "debug"]


class Outputs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    artifact_level: ArtifactLevel = "basic"
    return_waveforms: bool = False


class SimulationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    v: str = Field(..., min_length=1)
    scenario: Scenario | None = None
    path: Path
    fiber: Fiber
    spans: Spans
    signal: Signal
    transceiver: Transceiver
    processing: Processing
    propagation: Propagation
    latency_model: LatencyModel
    runtime: Runtime
    outputs: Outputs

    @model_validator(mode="after")
    def _cross_checks(self) -> SimulationSpec:
        fmt = self.signal.format
        if fmt == "coherent_qpsk":
            if self.transceiver.rx.coherent is not True:
                raise ValueError("transceiver.rx.coherent must be true for coherent_qpsk")
            if self.signal.n_pol != 2:
                raise ValueError("signal.n_pol must be 2 for coherent_qpsk")
        else:
            if self.transceiver.rx.coherent is not False:
                raise ValueError("transceiver.rx.coherent must be false for IM/DD formats")
            if self.signal.n_pol != 1:
                raise ValueError("signal.n_pol must be 1 for IM/DD formats")
            if self.propagation.model != "scalar_glnse":
                raise ValueError(
                    "propagation.model must be 'scalar_glnse' for IM/DD formats in v0.2"
                )

        if self.propagation.model == "manakov" and self.signal.n_pol != 2:
            raise ValueError("manakov propagation requires signal.n_pol == 2")
        return self


def get_simulation_spec_schema() -> dict[str, Any]:
    return SimulationSpec.model_json_schema()


# -----------------------------
# Result models
# -----------------------------

ResultStatus = Literal["success", "error"]


class LatencyBudget(BaseModel):
    model_config = ConfigDict(extra="forbid")
    propagation_s: float = Field(..., ge=0)
    serialization_s: float = Field(..., ge=0)
    framing_overhead_s: float = Field(..., ge=0)
    dsp_group_delay_s: float = Field(..., ge=0)
    fec_block_s: float = Field(..., ge=0)
    hardware_pipeline_s: float = Field(..., ge=0)
    queueing_s: float = Field(..., ge=0)
    processing_s: float = Field(..., ge=0)
    total_s: float = Field(..., ge=0)


class LatencyMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assumptions: list[str] = Field(default_factory=list)
    inputs_used: dict[str, Any] = Field(default_factory=dict)
    defaults_used: dict[str, Any] = Field(default_factory=dict)
    schema_version: str


class Throughput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    raw_line_rate: float = Field(..., ge=0)
    net_after_fec: float = Field(..., ge=0)
    goodput_est: float = Field(..., ge=0)


class Errors(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pre_fec_ber: float = Field(..., ge=0)
    post_fec_ber: float = Field(..., ge=0)
    fer: float = Field(..., ge=0)


class Summary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    latency_s: LatencyBudget
    latency_metadata: LatencyMetadata
    throughput_bps: Throughput
    errors: Errors
    osnr_db: float | None = None
    snr_db: float | None = None
    evm_rms: float | None = None
    q_factor_db: float | None = None


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sim_version: str
    spec_hash: str
    seed: int
    runtime_s: float = Field(..., ge=0)
    backend: str | None = None
    model: str | None = None


ArtifactType = Literal["png", "npz", "json", "txt", "bin"]


class Artifact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    type: ArtifactType
    ref: str
    mime: str | None = None
    bytes: int | None = Field(None, ge=0)


ErrorCode = Literal["validation_error", "runtime_error", "timeout", "not_implemented"]


class ErrorInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: ErrorCode
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class SimulationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    v: str = Field(..., min_length=1)
    status: ResultStatus
    summary: Summary | None = None
    error: ErrorInfo | None = None
    provenance: Provenance
    warnings: list[str] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    best_found_spec_patch: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _check_status(self) -> SimulationResult:
        if self.status == "success":
            if self.summary is None:
                raise ValueError("summary is required when status == 'success'")
            if self.error is not None:
                raise ValueError("error must be omitted when status == 'success'")
        else:
            if self.error is None:
                raise ValueError("error is required when status == 'error'")
            if self.summary is not None:
                raise ValueError("summary must be omitted when status == 'error'")
        return self


def get_simulation_result_schema() -> dict[str, Any]:
    return SimulationResult.model_json_schema()

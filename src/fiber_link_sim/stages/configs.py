from __future__ import annotations

from dataclasses import dataclass

from phys_pipeline import StageConfig  # type: ignore[import-untyped]

from fiber_link_sim.data_models.stage_models import (
    ArtifactsSpecSlice,
    ChannelSpecSlice,
    DspSpecSlice,
    FecSpecSlice,
    MetricsSpecSlice,
    RxFrontEndSpecSlice,
    TxSpecSlice,
)


@dataclass(frozen=True, slots=True)
class TxStageConfig(StageConfig):
    spec: TxSpecSlice
    name: str = "tx"


@dataclass(frozen=True, slots=True)
class ChannelStageConfig(StageConfig):
    spec: ChannelSpecSlice
    name: str = "channel"


@dataclass(frozen=True, slots=True)
class RxFrontEndStageConfig(StageConfig):
    spec: RxFrontEndSpecSlice
    name: str = "rx_frontend"


@dataclass(frozen=True, slots=True)
class DSPStageConfig(StageConfig):
    spec: DspSpecSlice
    name: str = "dsp"


@dataclass(frozen=True, slots=True)
class FECStageConfig(StageConfig):
    spec: FecSpecSlice
    name: str = "fec"


@dataclass(frozen=True, slots=True)
class MetricsStageConfig(StageConfig):
    spec: MetricsSpecSlice
    name: str = "metrics"


@dataclass(frozen=True, slots=True)
class ArtifactsStageConfig(StageConfig):
    spec: ArtifactsSpecSlice
    name: str = "artifacts"

from __future__ import annotations

from phys_pipeline import StageConfig  # type: ignore[import-untyped]

from fiber_link_sim.data_models.spec_models import SimulationSpec


class TxStageConfig(StageConfig):
    name: str = "tx"
    spec: SimulationSpec


class ChannelStageConfig(StageConfig):
    name: str = "channel"
    spec: SimulationSpec


class RxFrontEndStageConfig(StageConfig):
    name: str = "rx_frontend"
    spec: SimulationSpec


class DSPStageConfig(StageConfig):
    name: str = "dsp"
    spec: SimulationSpec


class FECStageConfig(StageConfig):
    name: str = "fec"
    spec: SimulationSpec


class MetricsStageConfig(StageConfig):
    name: str = "metrics"
    spec: SimulationSpec

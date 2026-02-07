from __future__ import annotations

from phys_pipeline import SequentialPipeline  # type: ignore[import-untyped]

from fiber_link_sim.data_models.spec_models import SimulationSpec
from fiber_link_sim.stages.configs import (
    ArtifactsStageConfig,
    ChannelStageConfig,
    DSPStageConfig,
    FECStageConfig,
    MetricsStageConfig,
    RxFrontEndStageConfig,
    TxStageConfig,
)
from fiber_link_sim.stages.core import (
    ArtifactsStage,
    ChannelStage,
    DSPStage,
    FECStage,
    MetricsStage,
    RxFrontEndStage,
    TxStage,
)


def build_pipeline(spec: SimulationSpec) -> SequentialPipeline:
    stages = [
        TxStage(cfg=TxStageConfig(spec=spec)),
        ChannelStage(cfg=ChannelStageConfig(spec=spec)),
        RxFrontEndStage(cfg=RxFrontEndStageConfig(spec=spec)),
        DSPStage(cfg=DSPStageConfig(spec=spec)),
        FECStage(cfg=FECStageConfig(spec=spec)),
        MetricsStage(cfg=MetricsStageConfig(spec=spec)),
        ArtifactsStage(cfg=ArtifactsStageConfig(spec=spec)),
    ]
    return SequentialPipeline(stages, name="fiber_link_sim")

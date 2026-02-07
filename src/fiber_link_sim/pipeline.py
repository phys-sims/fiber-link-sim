from __future__ import annotations

from phys_pipeline import SequentialPipeline  # type: ignore[import-untyped]

from fiber_link_sim.data_models.spec_models import SimulationSpec
from fiber_link_sim.data_models.stage_models import (
    ArtifactsSpecSlice,
    ChannelSpecSlice,
    DspSpecSlice,
    FecSpecSlice,
    MetricsSpecSlice,
    RxFrontEndSpecSlice,
    TxSpecSlice,
)
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
        TxStage(cfg=TxStageConfig(name="tx", spec=TxSpecSlice.from_spec(spec))),
        ChannelStage(cfg=ChannelStageConfig(name="channel", spec=ChannelSpecSlice.from_spec(spec))),
        RxFrontEndStage(
            cfg=RxFrontEndStageConfig(name="rx_frontend", spec=RxFrontEndSpecSlice.from_spec(spec))
        ),
        DSPStage(cfg=DSPStageConfig(name="dsp", spec=DspSpecSlice.from_spec(spec))),
        FECStage(cfg=FECStageConfig(name="fec", spec=FecSpecSlice.from_spec(spec))),
        MetricsStage(cfg=MetricsStageConfig(name="metrics", spec=MetricsSpecSlice.from_spec(spec))),
        ArtifactsStage(
            cfg=ArtifactsStageConfig(name="artifacts", spec=ArtifactsSpecSlice.from_spec(spec))
        ),
    ]
    return SequentialPipeline(stages, name="fiber_link_sim")

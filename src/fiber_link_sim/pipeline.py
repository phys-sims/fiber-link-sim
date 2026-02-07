from __future__ import annotations

from collections.abc import Sequence

from fiber_link_sim.data_models.spec_models import SimulationSpec
from fiber_link_sim.stages.base import Stage
from fiber_link_sim.stages.core import (
    ChannelStage,
    DSPStage,
    FECStage,
    MetricsStage,
    RxFrontEndStage,
    TxStage,
)


def build_pipeline(spec: SimulationSpec) -> Sequence[Stage]:
    return [
        TxStage(spec=spec),
        ChannelStage(spec=spec),
        RxFrontEndStage(spec=spec),
        DSPStage(spec=spec),
        FECStage(spec=spec),
        MetricsStage(spec=spec),
    ]

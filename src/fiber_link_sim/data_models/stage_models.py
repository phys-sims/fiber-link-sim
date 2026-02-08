from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from fiber_link_sim.data_models.spec_models import (
    Fiber,
    LatencyModel,
    Outputs,
    Path,
    Processing,
    Propagation,
    Runtime,
    Signal,
    Spans,
    Transceiver,
)

if TYPE_CHECKING:
    from fiber_link_sim.data_models.spec_models import SimulationSpec


class SignalSpec(Protocol):
    @property
    def signal(self) -> Signal: ...


@dataclass(frozen=True, slots=True)
class TxSpecSlice:
    runtime: Runtime
    signal: Signal
    transceiver: Transceiver

    @classmethod
    def from_spec(cls, spec: SimulationSpec) -> TxSpecSlice:
        return cls(
            runtime=spec.runtime.model_copy(deep=True),
            signal=spec.signal.model_copy(deep=True),
            transceiver=spec.transceiver.model_copy(deep=True),
        )


@dataclass(frozen=True, slots=True)
class ChannelSpecSlice:
    path: Path
    spans: Spans
    fiber: Fiber
    propagation: Propagation
    signal: Signal
    runtime: Runtime
    transceiver: Transceiver

    @classmethod
    def from_spec(cls, spec: SimulationSpec) -> ChannelSpecSlice:
        return cls(
            path=spec.path.model_copy(deep=True),
            spans=spec.spans.model_copy(deep=True),
            fiber=spec.fiber.model_copy(deep=True),
            propagation=spec.propagation.model_copy(deep=True),
            signal=spec.signal.model_copy(deep=True),
            runtime=spec.runtime.model_copy(deep=True),
            transceiver=spec.transceiver.model_copy(deep=True),
        )


@dataclass(frozen=True, slots=True)
class RxFrontEndSpecSlice:
    signal: Signal
    runtime: Runtime
    transceiver: Transceiver

    @classmethod
    def from_spec(cls, spec: SimulationSpec) -> RxFrontEndSpecSlice:
        return cls(
            signal=spec.signal.model_copy(deep=True),
            runtime=spec.runtime.model_copy(deep=True),
            transceiver=spec.transceiver.model_copy(deep=True),
        )


@dataclass(frozen=True, slots=True)
class DspSpecSlice:
    processing: Processing
    signal: Signal
    runtime: Runtime
    fiber: Fiber
    path: Path

    @classmethod
    def from_spec(cls, spec: SimulationSpec) -> DspSpecSlice:
        return cls(
            processing=spec.processing.model_copy(deep=True),
            signal=spec.signal.model_copy(deep=True),
            runtime=spec.runtime.model_copy(deep=True),
            fiber=spec.fiber.model_copy(deep=True),
            path=spec.path.model_copy(deep=True),
        )


@dataclass(frozen=True, slots=True)
class FecSpecSlice:
    processing: Processing
    signal: Signal

    @classmethod
    def from_spec(cls, spec: SimulationSpec) -> FecSpecSlice:
        return cls(
            processing=spec.processing.model_copy(deep=True),
            signal=spec.signal.model_copy(deep=True),
        )


@dataclass(frozen=True, slots=True)
class MetricsSpecSlice:
    signal: Signal
    runtime: Runtime
    latency_model: LatencyModel
    processing: Processing
    fiber: Fiber
    path: Path

    @classmethod
    def from_spec(cls, spec: SimulationSpec) -> MetricsSpecSlice:
        return cls(
            signal=spec.signal.model_copy(deep=True),
            runtime=spec.runtime.model_copy(deep=True),
            latency_model=spec.latency_model.model_copy(deep=True),
            processing=spec.processing.model_copy(deep=True),
            fiber=spec.fiber.model_copy(deep=True),
            path=spec.path.model_copy(deep=True),
        )


@dataclass(frozen=True, slots=True)
class ArtifactsSpecSlice:
    outputs: Outputs
    runtime: Runtime
    signal: Signal

    @classmethod
    def from_spec(cls, spec: SimulationSpec) -> ArtifactsSpecSlice:
        return cls(
            outputs=spec.outputs.model_copy(deep=True),
            runtime=spec.runtime.model_copy(deep=True),
            signal=spec.signal.model_copy(deep=True),
        )


__all__ = [
    "ArtifactsSpecSlice",
    "ChannelSpecSlice",
    "DspSpecSlice",
    "FecSpecSlice",
    "MetricsSpecSlice",
    "RxFrontEndSpecSlice",
    "SignalSpec",
    "TxSpecSlice",
]

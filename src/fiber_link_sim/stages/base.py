from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class State:
    meta: dict[str, Any] = field(default_factory=dict)
    tx: dict[str, Any] = field(default_factory=dict)
    optical: dict[str, Any] = field(default_factory=dict)
    rx: dict[str, Any] = field(default_factory=dict)
    stats: dict[str, Any] = field(default_factory=dict)
    artifacts: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class StageResult:
    state: State
    metrics: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)


class Stage:
    name: str = "stage"

    def run(self, state: State) -> StageResult:
        raise NotImplementedError

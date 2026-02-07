from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from optic.utils import parameters  # type: ignore[import-untyped]


@dataclass(slots=True)
class TxOutput:
    signal: np.ndarray
    symbols: np.ndarray
    params: parameters


@dataclass(slots=True)
class ChannelOutput:
    signal: np.ndarray
    params: parameters
    osnr_db: float | None
    n_spans: int


@dataclass(slots=True)
class RxOutput:
    samples: np.ndarray
    params: dict[str, Any]


@dataclass(slots=True)
class DspOutput:
    symbols: np.ndarray
    params: dict[str, Any]

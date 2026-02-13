from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator


@contextmanager
def env_overrides(pairs: dict[str, str]) -> Iterator[None]:
    """Temporarily override environment variables and restore previous values."""
    original: dict[str, str | None] = {key: os.environ.get(key) for key in pairs}
    try:
        for key, value in pairs.items():
            os.environ[key] = value
        yield
    finally:
        for key, previous in original.items():
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous

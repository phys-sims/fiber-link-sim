from __future__ import annotations

import datetime as _datetime


def ensure_datetime_utc() -> None:
    """Backfill ``datetime.UTC`` for Python < 3.11 before phys-pipeline imports."""
    if hasattr(_datetime, "UTC"):
        return
    _datetime.UTC = _datetime.timezone.utc



ensure_datetime_utc()

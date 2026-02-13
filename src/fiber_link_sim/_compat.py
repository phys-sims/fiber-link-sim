from __future__ import annotations

import datetime as _datetime


def ensure_datetime_utc() -> None:
    """Backfill ``datetime.UTC`` for Python < 3.11 before phys-pipeline imports."""
    if hasattr(_datetime, "UTC"):
        return
    utc = _datetime.timezone.__dict__["utc"]
    setattr(_datetime, "UTC", utc)


ensure_datetime_utc()

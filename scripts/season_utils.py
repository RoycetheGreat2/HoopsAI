"""NBA season end-year helpers (B-Ref convention: 2025-26 -> 2026)."""

from __future__ import annotations

import pandas as pd


def nba_season_end_year(dt) -> int | None:
    """Return B-Ref season end year from a game date (Oct–Jun cycle)."""
    if dt is None or (isinstance(dt, float) and pd.isna(dt)):
        return None
    ts = pd.Timestamp(dt)
    if ts.month >= 10:
        return int(ts.year + 1)
    return int(ts.year)

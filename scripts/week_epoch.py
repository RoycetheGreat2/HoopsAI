"""
7-day epochs anchored at MIN_TRACK_DATE (e.g. 2026-05-22 → 05-22..05-28, then 05-29..06-04).
"""
from __future__ import annotations

from datetime import date, timedelta

DEFAULT_ANCHOR = date(2026, 5, 22)


def epoch_week_start(d: date, anchor: date = DEFAULT_ANCHOR) -> date:
    """First day of the 7-day block containing ``d``."""
    if d < anchor:
        return anchor
    days = (d - anchor).days
    return anchor + timedelta(days=(days // 7) * 7)


def epoch_week_end(week_start: date) -> date:
    return week_start + timedelta(days=6)


def is_current_epoch_week(week_start: date, today: date | None = None) -> bool:
    today = today or date.today()
    return week_start == epoch_week_start(today)


def max_epoch_week_start(today: date, anchor: date = DEFAULT_ANCHOR) -> date:
    """Latest epoch start that still fits the forward-looking schedule window."""
    return epoch_week_start(today + timedelta(days=6), anchor)

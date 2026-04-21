import re
from datetime import date, timedelta
from typing import Any

from .constants import WEEKDAY_NAMES
from .utils import _today


def _this_week_range(today: date) -> tuple[date, date]:
    start_date = today - timedelta(days=today.weekday())
    end_date = start_date + timedelta(days=6)
    return start_date, end_date

def _last_week_range(today: date) -> tuple[date, date]:
    this_week_start, _ = _this_week_range(today)
    start_date = this_week_start - timedelta(days=7)
    end_date = start_date + timedelta(days=6)
    return start_date, end_date

def _this_weekend_range(today: date) -> tuple[date, date]:
    saturday_offset = (5 - today.weekday()) % 7
    start_date = today + timedelta(days=saturday_offset)
    end_date = start_date + timedelta(days=1)
    if today.weekday() == 6:
        start_date = today - timedelta(days=1)
        end_date = today
    return start_date, end_date

def _last_weekend_range(today: date) -> tuple[date, date]:
    this_week_start, _ = _this_week_range(today)
    end_date = this_week_start - timedelta(days=1)
    start_date = end_date - timedelta(days=1)
    return start_date, end_date

def _next_weekday(today: date, target_weekday: int) -> date:
    delta = (target_weekday - today.weekday()) % 7
    if delta == 0:
        delta = 7
    return today + timedelta(days=delta)

def _previous_weekday(today: date, target_weekday: int) -> date:
    delta = (today.weekday() - target_weekday) % 7
    if delta == 0:
        delta = 7
    return today - timedelta(days=delta)

def _detect_time_request(user_text: str) -> dict[str, Any]:
    lower = user_text.lower()
    today = _today()

    if "day after tomorrow" in lower:
        target_date = today + timedelta(days=2)
        return {"kind": "date", "label": "the day after tomorrow", "target_date": target_date}

    if "last weekend" in lower:
        start_date, end_date = _last_weekend_range(today)
        return {
            "kind": "range",
            "label": "last weekend",
            "start_date": start_date,
            "end_date": end_date,
        }

    if "this weekend" in lower:
        start_date, end_date = _this_weekend_range(today)
        return {
            "kind": "range",
            "label": "this weekend",
            "start_date": start_date,
            "end_date": end_date,
        }

    if "last week" in lower:
        start_date, end_date = _last_week_range(today)
        return {
            "kind": "range",
            "label": "last week",
            "start_date": start_date,
            "end_date": end_date,
        }

    if "this week" in lower:
        start_date, end_date = _this_week_range(today)
        return {
            "kind": "range",
            "label": "this week",
            "start_date": start_date,
            "end_date": end_date,
        }

    if "yesterday" in lower:
        target_date = today - timedelta(days=1)
        return {"kind": "date", "label": "yesterday", "target_date": target_date}

    if "tomorrow" in lower:
        target_date = today + timedelta(days=1)
        return {"kind": "date", "label": "tomorrow", "target_date": target_date}

    if "today" in lower or "right now" in lower or "currently" in lower or "now" in lower:
        return {"kind": "current", "label": "today", "target_date": today}

    for weekday_name, weekday_index in WEEKDAY_NAMES.items():
        if f"next {weekday_name}" in lower:
            target_date = _next_weekday(today, weekday_index)
            return {"kind": "date", "label": f"next {weekday_name}", "target_date": target_date}

        if f"last {weekday_name}" in lower:
            target_date = _previous_weekday(today, weekday_index)
            return {"kind": "date", "label": f"last {weekday_name}", "target_date": target_date}

        if re.search(rf"\b{weekday_name}\b", lower):
            target_date = today + timedelta(days=(weekday_index - today.weekday()) % 7)
            return {"kind": "date", "label": weekday_name, "target_date": target_date}

    return {"kind": "current", "label": "today", "target_date": today}
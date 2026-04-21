import re
from datetime import date, datetime, timezone, tzinfo
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .constants import LOCAL_TIMEZONE, TRAILING_TIME_PHRASES, WEATHER_CODE_MAP


def _result_error(message: str, location: str | None = None) -> dict[str, Any]:
    result = {"success": False, "message": message}
    if location:
        result["location"] = location
    return result

def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _pick(values: Any, index: int) -> Any:
    if not isinstance(values, list):
        return None
    if index < 0 or index >= len(values):
        return None
    return values[index]

def _mean(values: list[Any]) -> float | None:
    numbers = [_safe_float(value) for value in values]
    filtered = [value for value in numbers if value is not None]
    if not filtered:
        return None
    return sum(filtered) / len(filtered)

def _max_value(values: list[Any]) -> float | None:
    numbers = [_safe_float(value) for value in values]
    filtered = [value for value in numbers if value is not None]
    return max(filtered) if filtered else None

def _min_value(values: list[Any]) -> float | None:
    numbers = [_safe_float(value) for value in values]
    filtered = [value for value in numbers if value is not None]
    return min(filtered) if filtered else None

def _round_or_none(value: Any, digits: int = 1) -> float | None:
    number = _safe_float(value)
    if number is None:
        return None
    return round(number, digits)

def _format_number(value: Any, digits: int = 1) -> str | None:
    number = _safe_float(value)
    if number is None:
        return None
    return f"{number:.{digits}f}"

def _describe_weather_code(code: Any) -> str:
    if code is None:
        return "weather data unavailable"

    try:
        return WEATHER_CODE_MAP[int(code)]
    except (KeyError, TypeError, ValueError):
        return "weather data unavailable"

def _get_local_tzinfo() -> tzinfo:
    if LOCAL_TIMEZONE:
        try:
            return ZoneInfo(LOCAL_TIMEZONE)
        except ZoneInfoNotFoundError:
            pass

    detected = datetime.now().astimezone().tzinfo
    return detected or timezone.utc

def _today() -> date:
    return datetime.now(_get_local_tzinfo()).date()

def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None

def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None

def _format_clock(value: str | None) -> str | None:
    dt = _parse_iso_datetime(value)
    if dt is None:
        return None
    return dt.strftime("%I:%M %p").lstrip("0")

def _day_name(value: str | None) -> str:
    parsed = _parse_iso_date(value)
    if parsed is None:
        return "Unknown"
    return parsed.strftime("%a")

def _clean_location(location: str | None) -> str:
    cleaned = re.sub(r"\s+", " ", (location or "")).strip(" ?.,!")
    lower = cleaned.lower()

    for phrase in TRAILING_TIME_PHRASES:
        suffix = f" {phrase}"
        if lower.endswith(suffix):
            cleaned = cleaned[: -len(suffix)].strip(" ?.,!")
            lower = cleaned.lower()
            break

    cleaned = re.sub(
        r"^(?:weather|forecast|temperature|humidity|wind|rain|report|status report)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip(" ?.,!")
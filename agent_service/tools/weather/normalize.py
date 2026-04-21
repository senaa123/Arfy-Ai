from datetime import date
from typing import Any

from .utils import (
    _day_name,
    _describe_weather_code,
    _format_clock,
    _format_number,
    _max_value,
    _mean,
    _min_value,
    _parse_iso_date,
    _parse_iso_datetime,
    _pick,
    _round_or_none,
    _safe_float,
)


def _build_hourly_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    hourly = data.get("hourly")
    if not isinstance(hourly, dict):
        return []

    times = hourly.get("time") or []
    rows: list[dict[str, Any]] = []

    for index, iso_time in enumerate(times):
        parsed = _parse_iso_datetime(iso_time)
        date_str = parsed.date().isoformat() if parsed else str(iso_time)[:10]
        code = _pick(hourly.get("weather_code"), index)
        rows.append(
            {
                "time": iso_time,
                "date": date_str,
                "clock": _format_clock(iso_time),
                "temperature_c": _round_or_none(_pick(hourly.get("temperature_2m"), index)),
                "feels_like_c": _round_or_none(_pick(hourly.get("apparent_temperature"), index)),
                "humidity_percent": _round_or_none(_pick(hourly.get("relative_humidity_2m"), index), 0),
                "precipitation_mm": _round_or_none(_pick(hourly.get("precipitation"), index)),
                "rain_mm": _round_or_none(_pick(hourly.get("rain"), index)),
                "rain_chance_percent": _round_or_none(
                    _pick(hourly.get("precipitation_probability"), index),
                    0,
                ),
                "wind_speed_kmh": _round_or_none(_pick(hourly.get("wind_speed_10m"), index)),
                "wind_gusts_kmh": _round_or_none(_pick(hourly.get("wind_gusts_10m"), index)),
                "description": _describe_weather_code(code),
                "weather_code": code,
            }
        )

    return rows

def _normalize_legacy_daily_item(item: dict[str, Any]) -> dict[str, Any]:
    temp = item.get("temp") or {}
    feels_like = item.get("feels_like") or {}
    humidity = item.get("humidity") or {}
    wind = item.get("wind") or {}
    precipitation = item.get("precipitation") or {}
    astronomy = item.get("astronomy") or {}
    hourly_breakdown = item.get("hourly_breakdown") or []
    weather = item.get("weather") or [{"description": item.get("description", "weather data unavailable")}]

    day_temp = _safe_float(temp.get("day"))
    min_temp = _safe_float(temp.get("min"))
    max_temp = _safe_float(temp.get("max"))
    if day_temp is None and min_temp is not None and max_temp is not None:
        day_temp = (min_temp + max_temp) / 2

    return {
        "date": item.get("date"),
        "day_name": item.get("day_name") or _day_name(item.get("date")),
        "temp": {
            "day": _round_or_none(day_temp),
            "min": _round_or_none(min_temp),
            "max": _round_or_none(max_temp),
        },
        "feels_like": {
            "day": _round_or_none(feels_like.get("day")),
            "min": _round_or_none(feels_like.get("min")),
            "max": _round_or_none(feels_like.get("max")),
        },
        "humidity": {
            "mean": _round_or_none(humidity.get("mean"), 0),
            "min": _round_or_none(humidity.get("min"), 0),
            "max": _round_or_none(humidity.get("max"), 0),
        },
        "wind": {
            "mean_kmh": _round_or_none(wind.get("mean_kmh")),
            "max_kmh": _round_or_none(wind.get("max_kmh")),
            "gusts_max_kmh": _round_or_none(wind.get("gusts_max_kmh")),
        },
        "precipitation": {
            "total_mm": _round_or_none(precipitation.get("total_mm")),
            "rain_mm": _round_or_none(precipitation.get("rain_mm")),
            "chance_max_percent": _round_or_none(precipitation.get("chance_max_percent"), 0),
            "coverage_percent": _round_or_none(precipitation.get("coverage_percent"), 0),
        },
        "astronomy": {
            "sunrise": astronomy.get("sunrise"),
            "sunset": astronomy.get("sunset"),
        },
        "weather": weather,
        "hourly_breakdown": hourly_breakdown,
    }

def _normalize_daily_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    daily = data.get("daily")
    if isinstance(daily, list):
        return [_normalize_legacy_daily_item(item) for item in daily]

    if not isinstance(daily, dict):
        return []

    hourly_rows = _build_hourly_rows(data)
    by_date: dict[str, list[dict[str, Any]]] = {}
    for row in hourly_rows:
        by_date.setdefault(row["date"], []).append(row)

    items: list[dict[str, Any]] = []
    for index, day_value in enumerate(daily.get("time") or []):
        day_rows = by_date.get(day_value, [])
        code = _pick(daily.get("weather_code"), index)
        mean_temp = _safe_float(_pick(daily.get("temperature_2m_mean"), index))
        min_temp = _safe_float(_pick(daily.get("temperature_2m_min"), index))
        max_temp = _safe_float(_pick(daily.get("temperature_2m_max"), index))
        if mean_temp is None and min_temp is not None and max_temp is not None:
            mean_temp = (min_temp + max_temp) / 2

        mean_feels = _safe_float(_pick(daily.get("apparent_temperature_mean"), index))
        if mean_feels is None:
            mean_feels = _mean([row.get("feels_like_c") for row in day_rows])

        humidity_mean = _safe_float(_pick(daily.get("relative_humidity_2m_mean"), index))
        humidity_min = _safe_float(_pick(daily.get("relative_humidity_2m_min"), index))
        humidity_max = _safe_float(_pick(daily.get("relative_humidity_2m_max"), index))
        if humidity_mean is None:
            humidity_mean = _mean([row.get("humidity_percent") for row in day_rows])
        if humidity_min is None:
            humidity_min = _min_value([row.get("humidity_percent") for row in day_rows])
        if humidity_max is None:
            humidity_max = _max_value([row.get("humidity_percent") for row in day_rows])

        chance_max = _safe_float(_pick(daily.get("precipitation_probability_max"), index))
        if chance_max is None:
            chance_max = _max_value([row.get("rain_chance_percent") for row in day_rows])

        rainy_hours = [
            row
            for row in day_rows
            if (_safe_float(row.get("rain_mm")) or 0) > 0 or (_safe_float(row.get("precipitation_mm")) or 0) > 0
        ]
        coverage_percent = None
        if day_rows:
            coverage_percent = round((len(rainy_hours) / len(day_rows)) * 100, 0)

        items.append(
            {
                "date": day_value,
                "day_name": _day_name(day_value),
                "temp": {
                    "day": _round_or_none(mean_temp),
                    "min": _round_or_none(min_temp),
                    "max": _round_or_none(max_temp),
                },
                "feels_like": {
                    "day": _round_or_none(mean_feels),
                    "min": _round_or_none(_pick(daily.get("apparent_temperature_min"), index)),
                    "max": _round_or_none(_pick(daily.get("apparent_temperature_max"), index)),
                },
                "humidity": {
                    "mean": _round_or_none(humidity_mean, 0),
                    "min": _round_or_none(humidity_min, 0),
                    "max": _round_or_none(humidity_max, 0),
                },
                "wind": {
                    "mean_kmh": _round_or_none(_pick(daily.get("wind_speed_10m_mean"), index)),
                    "max_kmh": _round_or_none(_pick(daily.get("wind_speed_10m_max"), index)),
                    "gusts_max_kmh": _round_or_none(_pick(daily.get("wind_gusts_10m_max"), index)),
                },
                "precipitation": {
                    "total_mm": _round_or_none(_pick(daily.get("precipitation_sum"), index)),
                    "rain_mm": _round_or_none(_pick(daily.get("rain_sum"), index)),
                    "chance_max_percent": _round_or_none(chance_max, 0),
                    "coverage_percent": _round_or_none(coverage_percent, 0),
                },
                "astronomy": {
                    "sunrise": _format_clock(_pick(daily.get("sunrise"), index)),
                    "sunset": _format_clock(_pick(daily.get("sunset"), index)),
                },
                "weather": [{"description": _describe_weather_code(code), "code": code}],
                "hourly_breakdown": day_rows,
            }
        )

    return items

def _description_from_item(item: dict[str, Any]) -> str:
    weather_list = item.get("weather") or []
    if weather_list and isinstance(weather_list[0], dict):
        return weather_list[0].get("description", "weather data unavailable")
    return "weather data unavailable"

def _slice_daily_items(items: list[dict[str, Any]], start_date: date, end_date: date) -> list[dict[str, Any]]:
    selected = []
    for item in items:
        parsed = _parse_iso_date(item.get("date"))
        if parsed is None:
            continue
        if start_date <= parsed <= end_date:
            selected.append(item)
    return selected

def _select_item_by_date(items: list[dict[str, Any]], target_date: date) -> dict[str, Any] | None:
    for item in items:
        if item.get("date") == target_date.isoformat():
            return item
    return None

def _merge_daily_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for item in items:
        day_value = item.get("date")
        if not day_value:
            continue
        merged[day_value] = item
    return [merged[key] for key in sorted(merged)]

def _hourly_preview(rows: list[dict[str, Any]], current_time: str | None = None, limit: int = 6) -> list[dict[str, Any]]:
    if not rows:
        return []

    ordered = sorted(rows, key=lambda row: row.get("time", ""))
    if current_time:
        ordered = [row for row in ordered if row.get("time", "") >= current_time] or ordered

    if len(ordered) <= limit:
        return ordered

    step = max(1, len(ordered) // limit)
    return ordered[::step][:limit]
import os
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(env_path)

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
DEFAULT_GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_GEO_URL = os.getenv("WEATHER_GEO_URL", DEFAULT_GEO_URL)
WEATHER_FORECAST_URL = os.getenv(
    "WEATHER_FORECAST_DETAIL_URL",
    "https://api.open-meteo.com/v1/forecast",
)
WEATHER_HISTORY_ARCHIVE_URL = os.getenv(
    "WEATHER_HISTORY_ARCHIVE_URL",
    "https://archive-api.open-meteo.com/v1/archive",
)
WEATHER_BASE_URL = WEATHER_FORECAST_URL
FORECAST_DAYS_LIMIT = max(1, min(int(os.getenv("WEATHER_FORECAST_DAYS", "8")), 16))
HISTORY_DAYS_LIMIT = max(14, min(int(os.getenv("WEATHER_HISTORY_DAYS", "30")), 90))
LOCAL_TIMEZONE = (os.getenv("WEATHER_TIMEZONE") or "").strip()

CURRENT_FIELDS = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation",
    "rain",
    "weather_code",
    "wind_speed_10m",
    "wind_gusts_10m",
]
HOURLY_FIELDS = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation_probability",
    "precipitation",
    "rain",
    "weather_code",
    "wind_speed_10m",
    "wind_gusts_10m",
]
FORECAST_DAILY_FIELDS = [
    "weather_code",
    "temperature_2m_mean",
    "temperature_2m_max",
    "temperature_2m_min",
    "apparent_temperature_mean",
    "apparent_temperature_max",
    "apparent_temperature_min",
    "relative_humidity_2m_mean",
    "relative_humidity_2m_max",
    "relative_humidity_2m_min",
    "precipitation_sum",
    "rain_sum",
    "precipitation_probability_max",
    "sunrise",
    "sunset",
    "wind_speed_10m_mean",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
]
HISTORICAL_DAILY_FIELDS = [
    "weather_code",
    "temperature_2m_mean",
    "temperature_2m_max",
    "temperature_2m_min",
    "apparent_temperature_mean",
    "apparent_temperature_max",
    "apparent_temperature_min",
    "relative_humidity_2m_mean",
    "relative_humidity_2m_max",
    "relative_humidity_2m_min",
    "precipitation_sum",
    "rain_sum",
    "sunrise",
    "sunset",
    "wind_speed_10m_mean",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
]

WEEKDAY_NAMES = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
TRAILING_TIME_PHRASES = [
    "day after tomorrow",
    "this weekend",
    "last weekend",
    "next weekend",
    "this week",
    "last week",
    "next week",
    "today",
    "tomorrow",
    "yesterday",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]
WEATHER_CODE_MAP = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast clouds",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    56: "light freezing drizzle",
    57: "dense freezing drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "heavy freezing rain",
    71: "slight snow fall",
    73: "moderate snow fall",
    75: "heavy snow fall",
    77: "snow grains",
    80: "slight rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    85: "slight snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with slight hail",
    99: "thunderstorm with heavy hail",
}


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


def _http_get_json(url: str, params: dict[str, Any]) -> Any:
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def _geocode_from_url(url: str, location: str) -> dict[str, Any]:
    if "openweathermap.org" in url:
        if not WEATHER_API_KEY:
            raise ValueError("OpenWeather geocoding requires WEATHER_API_KEY.")

        data = _http_get_json(
            url,
            {
                "q": location,
                "limit": 1,
                "appid": WEATHER_API_KEY,
            },
        )
        if not data:
            raise ValueError(f"No weather location found for {location}.")

        item = data[0]
        name = item.get("name") or location
        region = item.get("state")
        country = item.get("country")
        pieces = [name]
        if region:
            pieces.append(region)
        if country:
            pieces.append(country)

        return {
            "lat": item["lat"],
            "lon": item["lon"],
            "resolved_name": ", ".join(pieces),
        }

    data = _http_get_json(
        url,
        {
            "name": location,
            "count": 1,
            "language": "en",
            "format": "json",
        },
    )
    results = data.get("results") or []
    if not results:
        raise ValueError(f"No weather location found for {location}.")

    item = results[0]
    name = item.get("name") or location
    region = item.get("admin1")
    country = item.get("country_code") or item.get("country")
    pieces = [name]
    if region:
        pieces.append(region)
    if country:
        pieces.append(country)

    return {
        "lat": item["latitude"],
        "lon": item["longitude"],
        "resolved_name": ", ".join(pieces),
    }


def _geocode_location(location: str) -> dict[str, Any]:
    cleaned = _clean_location(location)
    if not cleaned:
        return _result_error("No weather location was provided.")

    tried: list[str] = []
    for url in dict.fromkeys([WEATHER_GEO_URL, DEFAULT_GEO_URL]):
        try:
            return {"success": True, **_geocode_from_url(url, cleaned)}
        except Exception as exc:  # noqa: BLE001
            tried.append(str(exc))

    return _result_error(
        f"Failed to resolve weather request for {cleaned}: {tried[-1]}",
        cleaned,
    )


def _fetch_forecast_bundle(location: str) -> dict[str, Any]:
    geo = _geocode_location(location)
    if not geo.get("success"):
        return geo

    try:
        data = _http_get_json(
            WEATHER_FORECAST_URL,
            {
                "latitude": geo["lat"],
                "longitude": geo["lon"],
                "timezone": "auto",
                "forecast_days": FORECAST_DAYS_LIMIT,
                "current": ",".join(CURRENT_FIELDS),
                "hourly": ",".join(HOURLY_FIELDS),
                "daily": ",".join(FORECAST_DAILY_FIELDS),
                "temperature_unit": "celsius",
                "wind_speed_unit": "kmh",
                "precipitation_unit": "mm",
            },
        )
    except Exception as exc:  # noqa: BLE001
        return _result_error(f"Failed to fetch forecast weather: {exc}", geo["resolved_name"])

    return {"success": True, "geo": geo, "data": data}


def _fetch_historical_range(location: str, start_date: date, end_date: date) -> dict[str, Any]:
    geo = _geocode_location(location)
    if not geo.get("success"):
        return geo

    try:
        data = _http_get_json(
            WEATHER_HISTORY_ARCHIVE_URL,
            {
                "latitude": geo["lat"],
                "longitude": geo["lon"],
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "timezone": "auto",
                "hourly": ",".join(field for field in HOURLY_FIELDS if field != "precipitation_probability"),
                "daily": ",".join(HISTORICAL_DAILY_FIELDS),
                "temperature_unit": "celsius",
                "wind_speed_unit": "kmh",
                "precipitation_unit": "mm",
            },
        )
    except Exception as exc:  # noqa: BLE001
        return _result_error(f"Failed to fetch historical weather: {exc}", geo["resolved_name"])

    return {"success": True, "geo": geo, "data": data}


def _fetch_historical_day(location: str, target_date: date) -> dict[str, Any]:
    return _fetch_historical_range(location, target_date, target_date)


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


def _format_hourly_line(row: dict[str, Any], historical: bool = False) -> str:
    parts = []

    if row.get("temperature_c") is not None:
        parts.append(f"{_format_number(row['temperature_c'])} C")
    if row.get("feels_like_c") is not None:
        parts.append(f"feels {_format_number(row['feels_like_c'])} C")
    if row.get("humidity_percent") is not None:
        parts.append(f"humidity {int(row['humidity_percent'])}%")
    if row.get("wind_speed_kmh") is not None:
        parts.append(f"wind {_format_number(row['wind_speed_kmh'])} km/h")
    if row.get("rain_mm") is not None:
        parts.append(f"rain {_format_number(row['rain_mm'])} mm")
    elif row.get("precipitation_mm") is not None:
        parts.append(f"precip {_format_number(row['precipitation_mm'])} mm")

    if row.get("rain_chance_percent") is not None and not historical:
        parts.append(f"{int(row['rain_chance_percent'])}% rain chance")

    detail = ", ".join(parts)
    label = row.get("clock") or row.get("time") or "time unknown"
    description = row.get("description") or "weather data unavailable"
    return f"{label}: {description}; {detail}" if detail else f"{label}: {description}"


def _current_result_from_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    if not bundle.get("success", True):
        return bundle

    data = bundle.get("data") or {}
    daily_items = _normalize_daily_items(data)
    if not daily_items:
        return _result_error("No current weather data was returned.", bundle["geo"]["resolved_name"])

    today_item = daily_items[0]
    current = data.get("current") or {}
    current_time = current.get("time")
    hourly_breakdown = _hourly_preview(today_item.get("hourly_breakdown", []), current_time=current_time)

    description = _describe_weather_code(current.get("weather_code"))
    if description == "weather data unavailable":
        description = _description_from_item(today_item)

    rain_chance = today_item["precipitation"].get("chance_max_percent")
    rain_total = today_item["precipitation"].get("rain_mm")
    summary_parts = []

    if current.get("temperature_2m") is not None:
        summary_parts.append(f"{_format_number(current.get('temperature_2m'))} C")
    if current.get("apparent_temperature") is not None:
        summary_parts.append(f"feels like {_format_number(current.get('apparent_temperature'))} C")
    if current.get("relative_humidity_2m") is not None:
        summary_parts.append(f"humidity {int(round(float(current.get('relative_humidity_2m'))))}%")
    if current.get("wind_speed_10m") is not None:
        wind_text = f"wind {_format_number(current.get('wind_speed_10m'))} km/h"
        if current.get("wind_gusts_10m") is not None:
            wind_text += f", gusts {_format_number(current.get('wind_gusts_10m'))} km/h"
        summary_parts.append(wind_text)
    if current.get("rain") is not None or current.get("precipitation") is not None:
        amount = current.get("rain") if current.get("rain") is not None else current.get("precipitation")
        summary_parts.append(f"precipitation now {_format_number(amount)} mm")
    if rain_total is not None:
        rain_text = f"today's rain total {_format_number(rain_total)} mm"
        if rain_chance is not None:
            rain_text += f" with up to {int(rain_chance)}% chance"
        summary_parts.append(rain_text)
    if today_item["temp"].get("max") is not None and today_item["temp"].get("min") is not None:
        summary_parts.append(
            f"high/low {_format_number(today_item['temp']['max'])}/{_format_number(today_item['temp']['min'])} C"
        )
    if today_item["astronomy"].get("sunrise") and today_item["astronomy"].get("sunset"):
        summary_parts.append(
            f"sunrise {today_item['astronomy']['sunrise']}, sunset {today_item['astronomy']['sunset']}"
        )

    message = f"Current weather in {bundle['geo']['resolved_name']}: {description}. "
    if summary_parts:
        message += ". ".join(summary_parts) + "."
    if hourly_breakdown:
        message += "\nHourly breakdown:\n" + "\n".join(
            f"- {_format_hourly_line(row)}" for row in hourly_breakdown
        )

    return {
        "success": True,
        "kind": "current",
        "location": bundle["geo"]["resolved_name"],
        "target_date": today_item.get("date"),
        "temperature_c": _round_or_none(current.get("temperature_2m")),
        "feels_like_c": _round_or_none(current.get("apparent_temperature")),
        "humidity_percent": _round_or_none(current.get("relative_humidity_2m"), 0),
        "wind_speed_kmh": _round_or_none(current.get("wind_speed_10m")),
        "wind_gusts_kmh": _round_or_none(current.get("wind_gusts_10m")),
        "precipitation_mm": _round_or_none(current.get("precipitation")),
        "rain_mm": _round_or_none(current.get("rain")),
        "rain_chance_percent": _round_or_none(rain_chance, 0),
        "high_temp_c": today_item["temp"].get("max"),
        "low_temp_c": today_item["temp"].get("min"),
        "sunrise": today_item["astronomy"].get("sunrise"),
        "sunset": today_item["astronomy"].get("sunset"),
        "description": description,
        "hourly_breakdown": hourly_breakdown,
        "per_day": [today_item],
        "message": message,
    }


def _build_day_result(
    kind: str,
    location: str,
    label: str,
    target_date: date,
    item: dict[str, Any],
    historical: bool,
) -> dict[str, Any]:
    description = _description_from_item(item)
    hourly_breakdown = _hourly_preview(item.get("hourly_breakdown", []))
    precipitation = item.get("precipitation", {})
    rain_chance = precipitation.get("chance_max_percent")
    rain_total = precipitation.get("rain_mm")
    rain_coverage = precipitation.get("coverage_percent")

    summary_parts = []

    if item["temp"].get("day") is not None:
        summary_parts.append(f"average {_format_number(item['temp']['day'])} C")
    if item["temp"].get("max") is not None and item["temp"].get("min") is not None:
        summary_parts.append(
            f"high/low {_format_number(item['temp']['max'])}/{_format_number(item['temp']['min'])} C"
        )
    if item["feels_like"].get("day") is not None:
        summary_parts.append(f"feels like {_format_number(item['feels_like']['day'])} C")
    elif item["feels_like"].get("max") is not None and item["feels_like"].get("min") is not None:
        summary_parts.append(
            f"feels like {_format_number(item['feels_like']['max'])}/{_format_number(item['feels_like']['min'])} C"
        )
    if item["humidity"].get("mean") is not None:
        summary_parts.append(f"humidity {int(item['humidity']['mean'])}%")
    if item["wind"].get("mean_kmh") is not None:
        wind_text = f"wind {_format_number(item['wind']['mean_kmh'])} km/h"
        if item["wind"].get("gusts_max_kmh") is not None:
            wind_text += f", gusts up to {_format_number(item['wind']['gusts_max_kmh'])} km/h"
        summary_parts.append(wind_text)
    if rain_total is not None:
        rain_text = f"rain {_format_number(rain_total)} mm"
        if rain_chance is not None and not historical:
            rain_text += f", chance up to {int(rain_chance)}%"
        elif rain_coverage is not None:
            rain_text += f", recorded across {int(rain_coverage)}% of the sampled hours"
        summary_parts.append(rain_text)
    if item["astronomy"].get("sunrise") and item["astronomy"].get("sunset"):
        summary_parts.append(
            f"sunrise {item['astronomy']['sunrise']}, sunset {item['astronomy']['sunset']}"
        )

    message = f"Weather report for {location} {label} ({target_date.isoformat()}): {description}. "
    if summary_parts:
        message += ". ".join(summary_parts) + "."
    if hourly_breakdown:
        message += "\nHourly breakdown:\n" + "\n".join(
            f"- {_format_hourly_line(row, historical=historical)}" for row in hourly_breakdown
        )

    return {
        "success": True,
        "kind": kind,
        "location": location,
        "target_date": target_date.isoformat(),
        "temperature_c": item["temp"].get("day"),
        "average_temp_c": item["temp"].get("day"),
        "high_temp_c": item["temp"].get("max"),
        "low_temp_c": item["temp"].get("min"),
        "feels_like_c": item["feels_like"].get("day"),
        "humidity_percent": item["humidity"].get("mean"),
        "wind_speed_kmh": item["wind"].get("mean_kmh"),
        "wind_gusts_kmh": item["wind"].get("gusts_max_kmh"),
        "rain_mm": precipitation.get("rain_mm"),
        "precipitation_mm": precipitation.get("total_mm"),
        "rain_chance_percent": rain_chance,
        "rain_coverage_percent": rain_coverage,
        "sunrise": item["astronomy"].get("sunrise"),
        "sunset": item["astronomy"].get("sunset"),
        "description": description,
        "hourly_breakdown": hourly_breakdown,
        "per_day": [item],
        "message": message,
    }


def _build_range_result(
    kind: str,
    location: str,
    label: str,
    start_date: date,
    end_date: date,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    if not items:
        return _result_error(
            f"No weather data is available for {location} between {start_date.isoformat()} and {end_date.isoformat()}.",
            location,
        )

    descriptions = [_description_from_item(item) for item in items]
    dominant_description = Counter(descriptions).most_common(1)[0][0]
    avg_temp = _mean([item["temp"].get("day") for item in items])
    min_temp = _min_value([item["temp"].get("min") for item in items])
    max_temp = _max_value([item["temp"].get("max") for item in items])
    avg_feels = _mean([item["feels_like"].get("day") for item in items])
    avg_humidity = _mean([item["humidity"].get("mean") for item in items])
    avg_wind = _mean([item["wind"].get("mean_kmh") for item in items])
    peak_wind = _max_value([item["wind"].get("max_kmh") for item in items])
    peak_gust = _max_value([item["wind"].get("gusts_max_kmh") for item in items])
    total_rain = sum((_safe_float(item["precipitation"].get("rain_mm")) or 0) for item in items)
    max_rain_chance = _max_value([item["precipitation"].get("chance_max_percent") for item in items])
    avg_rain_coverage = _mean([item["precipitation"].get("coverage_percent") for item in items])

    overview_parts = []
    if avg_temp is not None:
        overview_parts.append(f"average temperature {_format_number(avg_temp)} C")
    if max_temp is not None and min_temp is not None:
        overview_parts.append(f"daily highs/lows {_format_number(max_temp)}/{_format_number(min_temp)} C")
    if avg_feels is not None:
        overview_parts.append(f"average feels-like {_format_number(avg_feels)} C")
    if avg_humidity is not None:
        overview_parts.append(f"average humidity {int(round(avg_humidity))}%")
    if avg_wind is not None:
        wind_text = f"average wind {_format_number(avg_wind)} km/h"
        if peak_gust is not None:
            wind_text += f", peak gusts {_format_number(peak_gust)} km/h"
        elif peak_wind is not None:
            wind_text += f", peak wind {_format_number(peak_wind)} km/h"
        overview_parts.append(wind_text)
    if total_rain:
        rain_text = f"rain total {total_rain:.1f} mm"
        if max_rain_chance is not None:
            rain_text += f", chance peaked at {int(max_rain_chance)}%"
        elif avg_rain_coverage is not None:
            rain_text += f", rain was recorded during about {int(round(avg_rain_coverage))}% of sampled hours"
        overview_parts.append(rain_text)

    per_day_lines = []
    for item in items:
        line_parts = []
        if item["temp"].get("max") is not None and item["temp"].get("min") is not None:
            line_parts.append(
                f"high/low {_format_number(item['temp']['max'])}/{_format_number(item['temp']['min'])} C"
            )
        if item["feels_like"].get("day") is not None:
            line_parts.append(f"feels {_format_number(item['feels_like']['day'])} C")
        if item["humidity"].get("mean") is not None:
            line_parts.append(f"humidity {int(item['humidity']['mean'])}%")
        if item["wind"].get("mean_kmh") is not None:
            wind_line = f"wind {_format_number(item['wind']['mean_kmh'])} km/h"
            if item["wind"].get("gusts_max_kmh") is not None:
                wind_line += f", gusts {_format_number(item['wind']['gusts_max_kmh'])} km/h"
            line_parts.append(wind_line)
        if item["precipitation"].get("rain_mm") is not None:
            rain_line = f"rain {_format_number(item['precipitation']['rain_mm'])} mm"
            if item["precipitation"].get("chance_max_percent") is not None:
                rain_line += f", chance {int(item['precipitation']['chance_max_percent'])}%"
            elif item["precipitation"].get("coverage_percent") is not None:
                rain_line += f", wet hours {int(item['precipitation']['coverage_percent'])}%"
            line_parts.append(rain_line)
        if item["astronomy"].get("sunrise") and item["astronomy"].get("sunset"):
            line_parts.append(
                f"sunrise {item['astronomy']['sunrise']}, sunset {item['astronomy']['sunset']}"
            )

        per_day_lines.append(
            f"- {item['day_name']} {item['date']}: {_description_from_item(item)}; " + "; ".join(line_parts)
        )

    message = (
        f"Weather report for {location} {label} ({start_date.isoformat()} to {end_date.isoformat()}): "
        f"{dominant_description}. "
    )
    if overview_parts:
        message += ". ".join(overview_parts) + "."
    message += "\nPer-day breakdown:\n" + "\n".join(per_day_lines)

    return {
        "success": True,
        "kind": kind,
        "location": location,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "average_temp_c": _round_or_none(avg_temp),
        "min_temp_c": _round_or_none(min_temp),
        "max_temp_c": _round_or_none(max_temp),
        "feels_like_c": _round_or_none(avg_feels),
        "humidity_percent": _round_or_none(avg_humidity, 0),
        "wind_speed_kmh": _round_or_none(avg_wind),
        "wind_gusts_kmh": _round_or_none(peak_gust),
        "rain_mm": round(total_rain, 1),
        "rain_chance_percent": _round_or_none(max_rain_chance, 0),
        "rain_coverage_percent": _round_or_none(avg_rain_coverage, 0),
        "description": dominant_description,
        "per_day": items,
        "message": message,
    }


def _fetch_current_weather(location: str) -> dict[str, Any]:
    bundle = _fetch_forecast_bundle(location)
    return _current_result_from_bundle(bundle)


def resolve_weather_request(user_text: str, location: str) -> dict[str, Any]:
    cleaned_location = _clean_location(location) or "Malabe"
    request = _detect_time_request(user_text)
    today = _today()

    if request["kind"] == "current":
        return _fetch_current_weather(cleaned_location)

    if request["kind"] == "date":
        target_date = request["target_date"]
        if target_date == today:
            return _fetch_current_weather(cleaned_location)

        if target_date > today:
            if (target_date - today).days > FORECAST_DAYS_LIMIT:
                return _result_error(
                    f"Forecast data is only available up to {FORECAST_DAYS_LIMIT} days ahead.",
                    cleaned_location,
                )

            bundle = _fetch_forecast_bundle(cleaned_location)
            if not bundle.get("success", True):
                return bundle

            item = _select_item_by_date(_normalize_daily_items(bundle.get("data") or {}), target_date)
            if item is None:
                return _result_error(
                    f"No forecast data is available for {cleaned_location} on {target_date.isoformat()}.",
                    bundle["geo"]["resolved_name"],
                )

            return _build_day_result(
                "forecast_day",
                bundle["geo"]["resolved_name"],
                request["label"],
                target_date,
                item,
                historical=False,
            )

        if (today - target_date).days > HISTORY_DAYS_LIMIT:
            return _result_error(
                f"Historical weather is only available up to {HISTORY_DAYS_LIMIT} days back.",
                cleaned_location,
            )

        bundle = _fetch_historical_day(cleaned_location, target_date)
        if not bundle.get("success", True):
            return bundle

        item = _select_item_by_date(_normalize_daily_items(bundle.get("data") or {}), target_date)
        if item is None:
            return _result_error(
                f"No historical data is available for {cleaned_location} on {target_date.isoformat()}.",
                bundle["geo"]["resolved_name"],
            )

        return _build_day_result(
            "historical_day",
            bundle["geo"]["resolved_name"],
            request["label"],
            target_date,
            item,
            historical=True,
        )

    start_date = request["start_date"]
    end_date = request["end_date"]
    all_items: list[dict[str, Any]] = []
    resolved_name = cleaned_location

    if start_date <= today - timedelta(days=1):
        historical_start = start_date
        historical_end = min(end_date, today - timedelta(days=1))
        if (today - historical_start).days > HISTORY_DAYS_LIMIT:
            return _result_error(
                f"Historical weather is only available up to {HISTORY_DAYS_LIMIT} days back.",
                cleaned_location,
            )

        history_bundle = _fetch_historical_range(cleaned_location, historical_start, historical_end)
        if not history_bundle.get("success", True):
            return history_bundle

        resolved_name = history_bundle["geo"]["resolved_name"]
        historical_items = _slice_daily_items(
            _normalize_daily_items(history_bundle.get("data") or {}),
            historical_start,
            historical_end,
        )
        all_items.extend(historical_items)

    if end_date >= today:
        forecast_start = max(start_date, today)
        if (end_date - today).days > FORECAST_DAYS_LIMIT:
            return _result_error(
                f"Forecast data is only available up to {FORECAST_DAYS_LIMIT} days ahead.",
                cleaned_location,
            )

        forecast_bundle = _fetch_forecast_bundle(cleaned_location)
        if not forecast_bundle.get("success", True):
            return forecast_bundle

        resolved_name = forecast_bundle["geo"]["resolved_name"]
        forecast_items = _slice_daily_items(
            _normalize_daily_items(forecast_bundle.get("data") or {}),
            forecast_start,
            end_date,
        )
        all_items.extend(forecast_items)

    merged_items = _merge_daily_items(all_items)

    if end_date < today:
        kind = "historical_range"
    elif start_date > today:
        kind = "forecast_range"
    else:
        kind = "mixed_range"

    return _build_range_result(
        kind,
        resolved_name,
        request["label"],
        start_date,
        end_date,
        merged_items,
    )


def get_weather(location: str) -> dict[str, Any]:
    return _fetch_current_weather(location)

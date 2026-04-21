from datetime import date
from typing import Any

from .constants import (
    CURRENT_FIELDS,
    FORECAST_DAYS_LIMIT,
    FORECAST_DAILY_FIELDS,
    HISTORICAL_DAILY_FIELDS,
    HOURLY_FIELDS,
    WEATHER_FORECAST_URL,
    WEATHER_HISTORY_ARCHIVE_URL,
)
from .formatters import _current_result_from_bundle
from .geo import _geocode_location, _http_get_json
from .utils import _result_error


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

def _fetch_current_weather(location: str) -> dict[str, Any]:
    bundle = _fetch_forecast_bundle(location)
    return _current_result_from_bundle(bundle)
from datetime import timedelta
from typing import Any

from .constants import FORECAST_DAYS_LIMIT, HISTORY_DAYS_LIMIT
from .fetchers import (
    _fetch_current_weather,
    _fetch_forecast_bundle,
    _fetch_historical_day,
    _fetch_historical_range,
)
from .formatters import _build_day_result, _build_range_result
from .normalize import _merge_daily_items, _normalize_daily_items, _select_item_by_date, _slice_daily_items
from .time_parser import _detect_time_request
from .utils import _clean_location, _result_error, _today


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
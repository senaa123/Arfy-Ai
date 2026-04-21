from typing import Any
from collections import Counter
from datetime import date

from .normalize import _description_from_item, _hourly_preview, _normalize_daily_items
from .utils import _describe_weather_code, _format_number, _max_value, _mean, _min_value, _result_error, _round_or_none, _safe_float


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
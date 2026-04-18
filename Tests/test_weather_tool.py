from datetime import date, timedelta
from zoneinfo import ZoneInfoNotFoundError

from agent_service.tools import weather


def _broken_zoneinfo(_name: str):
    raise ZoneInfoNotFoundError("missing tzdata")


def test_today_falls_back_when_zoneinfo_data_is_missing(monkeypatch):
    monkeypatch.setattr(weather, "LOCAL_TIMEZONE", "Asia/Colombo")
    monkeypatch.setattr(weather, "ZoneInfo", _broken_zoneinfo)

    assert isinstance(weather._today(), date)


def test_current_weather_request_survives_missing_zoneinfo_data(monkeypatch):
    monkeypatch.setattr(weather, "LOCAL_TIMEZONE", "Asia/Colombo")
    monkeypatch.setattr(weather, "ZoneInfo", _broken_zoneinfo)
    monkeypatch.setattr(weather, "WEATHER_API_KEY", "test-key")
    monkeypatch.setattr(
        weather,
        "_fetch_current_weather",
        lambda location: {
            "success": True,
            "kind": "current",
            "location": location,
            "message": f"Current weather for {location}",
        },
    )

    result = weather.resolve_weather_request("what is the weather in Colombo", "Colombo")

    assert result["success"] is True
    assert result["kind"] == "current"
    assert result["location"] == "Colombo"


def test_tomorrow_weather_request_survives_missing_zoneinfo_data(monkeypatch):
    monkeypatch.setattr(weather, "LOCAL_TIMEZONE", "Asia/Colombo")
    monkeypatch.setattr(weather, "ZoneInfo", _broken_zoneinfo)
    monkeypatch.setattr(weather, "WEATHER_API_KEY", "test-key")
    monkeypatch.setattr(weather, "FORECAST_DAYS_LIMIT", 8)
    today = weather._today()
    monkeypatch.setattr(
        weather,
        "_fetch_forecast_bundle",
        lambda _location: {
            "geo": {"resolved_name": "Colombo, LK"},
            "data": {
                "daily": [
                    {
                        "date": today.isoformat(),
                        "temp": {"day": 30},
                        "weather": [{"description": "sunny"}],
                    },
                    {
                        "date": (today + timedelta(days=1)).isoformat(),
                        "temp": {"day": 31},
                        "weather": [{"description": "few clouds"}],
                    },
                ]
            },
        },
    )

    result = weather.resolve_weather_request(
        "what is the weather tomorrow in Colombo",
        "Colombo",
    )

    assert result["success"] is True
    assert result["kind"] == "forecast_day"
    assert result["target_date"] == (today + timedelta(days=1)).isoformat()
    assert result["location"] == "Colombo, LK"
    assert result["temperature_c"] == 31


def test_yesterday_weather_request_uses_historical_archive(monkeypatch):
    monkeypatch.setattr(weather, "LOCAL_TIMEZONE", "Asia/Colombo")
    monkeypatch.setattr(weather, "ZoneInfo", _broken_zoneinfo)
    monkeypatch.setattr(weather, "WEATHER_API_KEY", "test-key")
    monkeypatch.setattr(weather, "HISTORY_DAYS_LIMIT", 7)
    today = weather._today()
    yesterday = today - timedelta(days=1)

    monkeypatch.setattr(
        weather,
        "_fetch_historical_range",
        lambda _location, _start, _end: {
            "geo": {"resolved_name": "Colombo, LK"},
            "data": {
                "daily": {
                    "time": [yesterday.isoformat()],
                    "temperature_2m_max": [31.0],
                    "temperature_2m_min": [25.0],
                    "weather_code": [61],
                }
            },
        },
    )

    result = weather.resolve_weather_request(
        "what was the weather yesterday in Colombo",
        "Colombo",
    )

    assert result["success"] is True
    assert result["kind"] == "historical_day"
    assert result["target_date"] == yesterday.isoformat()
    assert result["location"] == "Colombo, LK"
    assert result["average_temp_c"] == 28.0
    assert result["description"] == "slight rain"


def test_tomorrow_weather_request_includes_richer_report_fields(monkeypatch):
    monkeypatch.setattr(weather, "LOCAL_TIMEZONE", "Asia/Colombo")
    monkeypatch.setattr(weather, "ZoneInfo", _broken_zoneinfo)
    today = weather._today()
    tomorrow = today + timedelta(days=1)

    monkeypatch.setattr(
        weather,
        "_fetch_forecast_bundle",
        lambda _location: {
            "success": True,
            "geo": {"resolved_name": "Malabe, LK"},
            "data": {
                "daily": {
                    "time": [today.isoformat(), tomorrow.isoformat()],
                    "weather_code": [2, 61],
                    "temperature_2m_mean": [29.5, 27.8],
                    "temperature_2m_max": [31.2, 29.1],
                    "temperature_2m_min": [26.1, 25.2],
                    "apparent_temperature_mean": [31.4, 30.6],
                    "apparent_temperature_max": [33.0, 32.2],
                    "apparent_temperature_min": [27.5, 26.7],
                    "relative_humidity_2m_mean": [72, 84],
                    "relative_humidity_2m_max": [80, 91],
                    "relative_humidity_2m_min": [62, 74],
                    "precipitation_sum": [0.7, 8.4],
                    "rain_sum": [0.5, 7.9],
                    "precipitation_probability_max": [20, 85],
                    "sunrise": [f"{today.isoformat()}T05:58", f"{tomorrow.isoformat()}T05:58"],
                    "sunset": [f"{today.isoformat()}T18:18", f"{tomorrow.isoformat()}T18:18"],
                    "wind_speed_10m_mean": [9.0, 12.5],
                    "wind_speed_10m_max": [16.0, 18.4],
                    "wind_gusts_10m_max": [22.0, 26.3],
                },
                "hourly": {
                    "time": [
                        f"{tomorrow.isoformat()}T06:00",
                        f"{tomorrow.isoformat()}T09:00",
                        f"{tomorrow.isoformat()}T12:00",
                        f"{tomorrow.isoformat()}T15:00",
                    ],
                    "temperature_2m": [25.8, 27.1, 28.6, 27.9],
                    "relative_humidity_2m": [90, 86, 80, 82],
                    "apparent_temperature": [27.1, 29.5, 31.3, 30.8],
                    "precipitation_probability": [60, 85, 70, 55],
                    "precipitation": [0.6, 2.2, 3.5, 1.4],
                    "rain": [0.6, 2.0, 3.1, 1.2],
                    "weather_code": [61, 63, 63, 61],
                    "wind_speed_10m": [8.0, 11.0, 14.0, 13.0],
                    "wind_gusts_10m": [12.0, 17.0, 22.0, 21.0],
                },
            },
        },
    )

    result = weather.resolve_weather_request(
        "what is the weather tomorrow in Malabe",
        "Malabe",
    )

    assert result["success"] is True
    assert result["kind"] == "forecast_day"
    assert result["humidity_percent"] == 84
    assert result["wind_speed_kmh"] == 12.5
    assert result["rain_mm"] == 7.9
    assert result["rain_chance_percent"] == 85
    assert result["sunrise"] == "5:58 AM"
    assert result["sunset"] == "6:18 PM"
    assert len(result["hourly_breakdown"]) == 4
    assert "Hourly breakdown" in result["message"]


def test_last_week_weather_request_returns_per_day_breakdown(monkeypatch):
    monkeypatch.setattr(weather, "LOCAL_TIMEZONE", "Asia/Colombo")
    monkeypatch.setattr(weather, "ZoneInfo", _broken_zoneinfo)
    today = weather._today()
    start_date, end_date = weather._last_week_range(today)
    days = [start_date + timedelta(days=index) for index in range(7)]

    monkeypatch.setattr(
        weather,
        "_fetch_historical_range",
        lambda _location, _start, _end: {
            "success": True,
            "geo": {"resolved_name": "Malabe, LK"},
            "data": {
                "daily": {
                    "time": [day.isoformat() for day in days],
                    "weather_code": [3, 61, 61, 2, 80, 3, 2],
                    "temperature_2m_mean": [26.4, 26.8, 27.0, 27.5, 26.9, 26.3, 26.7],
                    "temperature_2m_max": [29.0, 29.4, 30.1, 31.0, 30.0, 28.8, 29.2],
                    "temperature_2m_min": [24.2, 24.8, 25.1, 25.6, 24.9, 24.0, 24.5],
                    "apparent_temperature_mean": [28.8, 29.1, 29.4, 30.0, 29.2, 28.4, 28.9],
                    "apparent_temperature_max": [31.2, 31.8, 32.1, 33.0, 32.4, 30.8, 31.0],
                    "apparent_temperature_min": [25.6, 26.0, 26.1, 26.8, 26.0, 25.1, 25.3],
                    "relative_humidity_2m_mean": [82, 84, 85, 80, 83, 86, 81],
                    "relative_humidity_2m_max": [91, 93, 94, 90, 92, 95, 90],
                    "relative_humidity_2m_min": [70, 72, 74, 69, 71, 75, 70],
                    "precipitation_sum": [1.5, 6.2, 7.0, 0.0, 3.8, 1.0, 0.2],
                    "rain_sum": [1.2, 5.8, 6.6, 0.0, 3.4, 0.9, 0.1],
                    "sunrise": [f"{day.isoformat()}T05:58" for day in days],
                    "sunset": [f"{day.isoformat()}T18:17" for day in days],
                    "wind_speed_10m_mean": [8.0, 9.2, 10.0, 11.1, 9.8, 8.4, 7.9],
                    "wind_speed_10m_max": [14.0, 16.5, 17.2, 18.4, 16.1, 14.4, 13.2],
                    "wind_gusts_10m_max": [20.0, 24.0, 25.1, 26.0, 23.0, 21.0, 19.0],
                },
                "hourly": {
                    "time": [
                        f"{day.isoformat()}T06:00"
                        for day in days
                    ] + [
                        f"{day.isoformat()}T15:00"
                        for day in days
                    ],
                    "temperature_2m": [24.8, 25.0, 25.2, 25.5, 25.1, 24.6, 24.8, 28.6, 29.0, 29.4, 30.2, 29.1, 28.0, 28.4],
                    "relative_humidity_2m": [90, 92, 93, 88, 91, 94, 89, 76, 80, 82, 75, 79, 84, 78],
                    "apparent_temperature": [26.0, 26.3, 26.4, 27.0, 26.5, 25.9, 26.0, 30.1, 30.5, 31.0, 31.8, 30.8, 29.5, 29.7],
                    "precipitation": [0.2, 0.8, 1.0, 0.0, 0.6, 0.1, 0.0, 1.0, 2.0, 2.2, 0.0, 1.3, 0.2, 0.0],
                    "rain": [0.2, 0.7, 0.9, 0.0, 0.5, 0.1, 0.0, 0.9, 1.9, 2.0, 0.0, 1.2, 0.2, 0.0],
                    "weather_code": [3, 61, 61, 2, 80, 3, 2, 3, 61, 61, 2, 80, 3, 2],
                    "wind_speed_10m": [7, 8, 8, 10, 9, 7, 7, 10, 11, 12, 13, 11, 9, 8],
                    "wind_gusts_10m": [11, 12, 13, 15, 14, 12, 11, 16, 18, 19, 20, 17, 15, 14],
                },
            },
        },
    )

    result = weather.resolve_weather_request(
        "give me the weather report for last week in Malabe",
        "Malabe",
    )

    assert result["success"] is True
    assert result["kind"] == "historical_range"
    assert len(result["per_day"]) == 7
    assert result["rain_mm"] == 18.0
    assert "Per-day breakdown" in result["message"]
    assert "humidity" in result["message"]
    assert "sunrise" in result["message"]


def test_this_week_weather_request_combines_history_and_forecast(monkeypatch):
    anchor_day = date(2026, 4, 15)
    monkeypatch.setattr(weather, "_today", lambda: anchor_day)
    start_date, end_date = weather._this_week_range(anchor_day)

    historical_days = [start_date, start_date + timedelta(days=1)]
    forecast_days = [anchor_day + timedelta(days=index) for index in range(0, 5)]

    monkeypatch.setattr(
        weather,
        "_fetch_historical_range",
        lambda _location, _start, _end: {
            "success": True,
            "geo": {"resolved_name": "Colombo, LK"},
            "data": {
                "daily": [
                    {
                        "date": historical_days[0].isoformat(),
                        "temp": {"day": 27.0, "min": 24.0, "max": 30.0},
                        "feels_like": {"day": 29.0},
                        "humidity": {"mean": 84},
                        "wind": {"mean_kmh": 9.0, "gusts_max_kmh": 14.0},
                        "precipitation": {"rain_mm": 3.0, "coverage_percent": 50},
                        "astronomy": {"sunrise": "5:58 AM", "sunset": "6:18 PM"},
                        "weather": [{"description": "slight rain"}],
                    },
                    {
                        "date": historical_days[1].isoformat(),
                        "temp": {"day": 27.4, "min": 24.5, "max": 30.2},
                        "feels_like": {"day": 29.2},
                        "humidity": {"mean": 82},
                        "wind": {"mean_kmh": 9.5, "gusts_max_kmh": 15.0},
                        "precipitation": {"rain_mm": 1.5, "coverage_percent": 25},
                        "astronomy": {"sunrise": "5:58 AM", "sunset": "6:18 PM"},
                        "weather": [{"description": "overcast clouds"}],
                    },
                ]
            },
        },
    )
    monkeypatch.setattr(
        weather,
        "_fetch_forecast_bundle",
        lambda _location: {
            "success": True,
            "geo": {"resolved_name": "Colombo, LK"},
            "data": {
                "daily": [
                    {
                        "date": day.isoformat(),
                        "temp": {"day": 28.0 + index, "min": 25.0, "max": 31.0 + index},
                        "feels_like": {"day": 30.0 + index},
                        "humidity": {"mean": 78 + index},
                        "wind": {"mean_kmh": 11.0 + index, "gusts_max_kmh": 17.0 + index},
                        "precipitation": {"rain_mm": 2.0 + index, "chance_max_percent": 40 + index * 5},
                        "astronomy": {"sunrise": "5:58 AM", "sunset": "6:18 PM"},
                        "weather": [{"description": "moderate rain" if index % 2 else "partly cloudy"}],
                    }
                    for index, day in enumerate(forecast_days)
                ]
            },
        },
    )

    result = weather.resolve_weather_request(
        "status report for the weather this week in Colombo",
        "Colombo",
    )

    assert result["success"] is True
    assert result["kind"] == "mixed_range"
    assert result["start_date"] == start_date.isoformat()
    assert result["end_date"] == end_date.isoformat()
    assert len(result["per_day"]) == 7
    assert result["per_day"][0]["date"] == start_date.isoformat()
    assert result["per_day"][-1]["date"] == end_date.isoformat()

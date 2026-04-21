import os
from pathlib import Path

from dotenv import load_dotenv

# Keep env loading close to weather config so split modules still share
# the same runtime configuration behavior as the old single-file tool.
env_path = Path(__file__).resolve().parents[2] / ".env"
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
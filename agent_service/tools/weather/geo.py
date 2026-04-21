from typing import Any

import requests

from .constants import DEFAULT_GEO_URL, WEATHER_API_KEY, WEATHER_GEO_URL
from .utils import _clean_location, _result_error


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
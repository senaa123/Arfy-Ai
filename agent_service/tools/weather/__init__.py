"""
Split weather tool package.

Phase 4B cleanup goal:
- keep the public weather entry points stable
- move parsing/fetching/normalization/formatting into focused modules
- avoid changing tool behavior while reducing file overload
"""

from .service import get_weather, resolve_weather_request

__all__ = ["get_weather", "resolve_weather_request"]
from __future__ import annotations

from agent_service.plugins.base import ToolContext, ToolPlugin, ToolSpec
from agent_service.tools.memory_tool import save_memory
from agent_service.tools.search import web_search
from agent_service.tools.weather import resolve_weather_request, get_weather


class WeatherToolPlugin(ToolPlugin):
    """
    Wraps the existing weather tool as a plugin.
    """

    spec = ToolSpec(
        name="weather",
        description="Resolve current, forecast, historical, and summary weather requests.",
        transport="local",
        supported_intents=["weather"],
        enabled=True,
        timeout_seconds=20,
    )

    def execute(self, context: ToolContext) -> dict:
        # Prefer router-extracted location if available
        location = context.extracted_data.get("location", "Malabe")

        # Full text is passed because weather tool may infer time range from raw text
        return resolve_weather_request(context.user_text, location)


class SearchToolPlugin(ToolPlugin):
    """
    Wraps the existing web search tool as a plugin.
    """

    spec = ToolSpec(
        name="search",
        description="Search the web and return compact results.",
        transport="local",
        supported_intents=["search"],
        enabled=True,
        timeout_seconds=15,
    )

    def execute(self, context: ToolContext) -> dict:
        # Use extracted query first, otherwise fall back to raw text
        query = context.extracted_data.get("query", context.user_text)
        return web_search(query)


class MemorySaveToolPlugin(ToolPlugin):
    """
    Wraps structured memory save as a plugin.
    """

    spec = ToolSpec(
        name="memory_save",
        description="Save structured durable memory through memory_service.",
        transport="local",
        supported_intents=["remember"],
        enabled=True,
        timeout_seconds=15,
    )

    def execute(self, context: ToolContext) -> dict:
        # Keep defaults here so router logic stays simpler
        value = context.extracted_data.get("value", context.user_text)
        key = context.extracted_data.get("key", "user_note")
        category = context.extracted_data.get("category", "facts")

        return save_memory(category, key, value)
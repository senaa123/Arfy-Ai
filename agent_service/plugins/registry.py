from __future__ import annotations

from typing import Dict, List, Optional

from agent_service.plugins.base import ToolPlugin
from agent_service.plugins.builtin_tools import (
    MemorySaveToolPlugin,
    SearchToolPlugin,
    WeatherToolPlugin,
)
from agent_service.plugins.document_tools import DocumentIngestToolPlugin


class ToolRegistry:
    """
    Central registry for all agent-callable tools.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, ToolPlugin] = {}

    def register(self, plugin: ToolPlugin) -> None:
        self._tools[plugin.spec.name] = plugin

    def get(self, tool_name: str | None) -> Optional[ToolPlugin]:
        if not tool_name:
            return None
        return self._tools.get(tool_name)

    def resolve_for_intent(self, intent: str | None) -> Optional[ToolPlugin]:
        if not intent:
            return None

        for plugin in self._tools.values():
            if plugin.spec.enabled and plugin.supports_intent(intent):
                return plugin

        return None

    def list_specs(self) -> List[dict]:
        return [plugin.spec.model_dump() for plugin in self._tools.values()]


registry = ToolRegistry()

# Built-in tools
registry.register(WeatherToolPlugin())
registry.register(SearchToolPlugin())
registry.register(MemorySaveToolPlugin())

# Remote capability tools
registry.register(DocumentIngestToolPlugin())
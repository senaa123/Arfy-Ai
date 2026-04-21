from __future__ import annotations

from agent_service.models import GraphState
from agent_service.plugins.base import ToolContext
from agent_service.plugins.registry import registry


def execute_registered_tool(
    *,
    session_id: str,
    user_text: str,
    tool_name: str | None,
    intent: str | None,
    extracted_data: dict | None,
    memories,
    history,
) -> tuple[str | None, dict]:
    """
    Resolve and execute a tool using the central registry.

    Resolution order:
    1. exact tool_name if router gave one
    2. fallback by intent
    """

    # First try exact tool name
    plugin = registry.get(tool_name)

    # If not found, try resolving by intent
    if plugin is None:
        plugin = registry.resolve_for_intent(intent)

    if plugin is None:
        return None, {
            "success": False,
            "message": f"No registered tool found for tool_name={tool_name!r} intent={intent!r}.",
        }

    if not plugin.spec.enabled:
        return plugin.spec.name, {
            "success": False,
            "message": f"Tool '{plugin.spec.name}' is currently disabled.",
        }

    # Build normalized tool input
    context = ToolContext(
        session_id=session_id,
        user_text=user_text,
        extracted_data=extracted_data or {},
        memories=memories,
        history=history,
    )

    # Execute actual tool/plugin
    result = plugin.execute(context)
    return plugin.spec.name, result


def execute_registered_tool_for_state(state: GraphState) -> GraphState:
    """
    Small helper for LangGraph nodes.
    """
    resolved_tool_name, tool_result = execute_registered_tool(
        session_id=state.session_id,
        user_text=state.user_text,
        tool_name=state.tool_name,
        intent=state.intent,
        extracted_data=state.extracted_data,
        memories=state.memories,
        history=state.history,
    )

    state.tool_used = resolved_tool_name
    state.tool_result = tool_result
    return state
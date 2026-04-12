from langgraph.graph import END, StateGraph

from agent_service.brain import build_final_response, llm_route
from agent_service.models import AgentAction, GraphState
from agent_service.safety import is_repeated_action, is_safe_action, validate_payload
from agent_service.tools.memory_tool import get_recent_action_history, save_memory
from agent_service.tools.search import web_search
from agent_service.tools.weather import resolve_weather_request


def route_node(state: GraphState) -> GraphState:
    """
    Use the LLM router to classify user intent.
    """
    decision = llm_route(
        user_text=state.user_text,
        memories=state.memories,
        history=state.history,
    )

    state.intent = decision.intent
    state.extracted_data = decision.extracted_data or {}
    state.confidence = decision.confidence
    state.tool_result = getattr(decision, "tool_result", None)

    if decision.action:
        if isinstance(decision.action, dict):
            state.action = AgentAction(**decision.action)
        else:
            state.action = decision.action

    return state


def tool_node(state: GraphState) -> GraphState:
    """
    Execute agent-side tool calls.
    """
    if state.intent == "weather":
        # Use the smarter weather resolver.
        # It reads the original user text and decides whether the user asked for:
        # current weather, future forecast, historical weather, week summary, or weekend summary.
        location = state.extracted_data.get("location", "Malabe")
        state.tool_result = resolve_weather_request(state.user_text, location)
        state.tool_used = "weather"

    elif state.intent == "search":
        query = state.extracted_data.get("query", state.user_text)
        state.tool_result = web_search(query)
        state.tool_used = "search"

    elif state.intent == "remember":
        value = state.extracted_data.get("value", state.user_text)
        key = state.extracted_data.get("key", "user_note")
        category = state.extracted_data.get("category", "facts")
        state.tool_result = save_memory(category, key, value)
        state.tool_used = "memory_save"

    return state


def safety_node(state: GraphState) -> GraphState:
    """
    Check whether a proposed action is safe and not repeating too much.
    """
    if state.action is None:
        return state

    action_type = state.action.type
    payload = state.action.payload

    if not is_safe_action(action_type):
        state.action = None
        state.tool_result = {"success": False, "message": "Unsafe action blocked"}
        return state

    if not validate_payload(action_type, payload):
        state.action = None
        state.tool_result = {"success": False, "message": "Invalid action payload"}
        return state

    history = get_recent_action_history(limit=10)

    if is_repeated_action(action_type, history):
        state.action = None
        state.tool_result = {
            "success": False,
            "message": "Repeated action blocked to prevent loops.",
        }
        return state

    return state


def response_node(state: GraphState) -> GraphState:
    """
    Generate the final spoken response.
    """
    action_dict = None

    if state.action:
        action_dict = {
            "type": state.action.type,
            "payload": state.action.payload,
        }

    state.response = build_final_response(
        user_text=state.user_text,
        intent=state.intent or "chat",
        tool_used=state.tool_used or "",
        tool_result=state.tool_result or {},
        action=action_dict,
        memories=state.memories,
        history=state.history,
    )
    return state


def should_use_tool(state: GraphState) -> str:
    """
    Decide the next graph node after routing.
    """
    if state.intent in {"weather", "search", "remember"}:
        return "tool"

    if state.action is not None:
        return "safety"

    return "response"


def build_graph():
    """
    Build and compile the LangGraph workflow.
    """
    workflow = StateGraph(GraphState)

    workflow.add_node("route", route_node)
    workflow.add_node("tool", tool_node)
    workflow.add_node("safety", safety_node)
    workflow.add_node("response", response_node)

    workflow.set_entry_point("route")

    workflow.add_conditional_edges(
        "route",
        should_use_tool,
        {
            "tool": "tool",
            "safety": "safety",
            "response": "response",
        },
    )

    workflow.add_edge("tool", "response")
    workflow.add_edge("safety", "response")
    workflow.add_edge("response", END)

    return workflow.compile()
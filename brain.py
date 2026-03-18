import json
import os
import re
import time
from datetime import datetime
from typing import Literal

import psutil
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_groq import ChatGroq

from apps import open_app
from memory import get_memory_text, load_memory, memory_save
from vector_memory import get_semantic_memory_context, sync_structured_memory
from weather import (
    get_day_forecast,
    get_forecast,
    get_tomorrow_forecast,
    get_weather,
)

load_dotenv()


MODEL_NAME = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# The assistant now uses three focused LLM roles instead of one overloaded agent:
# - llm_chat writes the final user-facing answer
# - llm_router decides whether the turn needs a tool
# - llm_tool makes the actual single-tool call with a tiny prompt
llm_chat = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model=MODEL_NAME,
    temperature=0.4,
    max_tokens=220,
)

llm_router = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model=MODEL_NAME,
    temperature=0,
    max_tokens=140,
)

llm_tool = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model=MODEL_NAME,
    temperature=0,
    max_tokens=180,
)


chat_history = ChatMessageHistory()


class RouteDecision(BaseModel):
    action: Literal[
        "chat",
        "search_web",
        "get_current_weather",
        "get_weather_forecast",
        "save_memory",
    ] = Field(description="The single best next step for this user turn.")
    tool_input: str = Field(
        default="",
        description="Exact input for the selected tool. Leave empty for chat.",
    )
    reply_intent: str = Field(
        default="",
        description="Short explanation of what the user wants.",
    )


ROUTER_PROMPT = """You are the routing model for Arfy.
Pick exactly one action for the user's request and return JSON only.

Allowed actions:
- chat
- search_web
- get_current_weather
- get_weather_forecast
- save_memory

Return this exact JSON shape:
{"action": "...", "tool_input": "...", "reply_intent": "..."}

Rules:
- Use search_web for latest news, current events, live topics, current facts, or anything that needs fresh web information.
- Use get_current_weather for weather right now or today's weather.
- Use get_weather_forecast for tomorrow, weekend, weekly, or named-day forecast requests.
- For get_current_weather, tool_input must be a location string or "auto".
- For get_weather_forecast, tool_input must be "location|target". Use "auto" if no location is given.
- Valid forecast targets: tomorrow, week, weekend, monday, tuesday, wednesday, thursday, friday, saturday, sunday.
- Use save_memory only if the user explicitly asks to remember, save, note, or not forget something.
- For save_memory, tool_input must be "category|key|value" and category must be personal, preferences, or facts.
- Use chat for everything else.

Examples:
User: How is the war in Iran?
{"action":"search_web","tool_input":"latest updates on the Iran war","reply_intent":"Get current war updates"}

User: What is the weather tomorrow?
{"action":"get_weather_forecast","tool_input":"auto|tomorrow","reply_intent":"Get tomorrow weather forecast"}

User: Remember that I live in Malabe
{"action":"save_memory","tool_input":"personal|location|Malabe","reply_intent":"Save location to memory"}

User: Tell me a joke
{"action":"chat","tool_input":"","reply_intent":"Answer casually"}
"""


TOOL_CALLER_PROMPT = """You are a precise function caller.
You have access to exactly one tool.
Call that tool exactly once.
Do not answer conversationally.
Do not output XML, markdown, or pseudo-function tags.
Return only a valid structured tool call for the provided tool.
"""


@tool
def search_web(query: str) -> str:
    """Search the web for current news, events, or real-time information."""
    try:
        search = DuckDuckGoSearchRun()
        return search.run(query)
    except Exception as exc:
        return f"Search failed: {exc}"


@tool
def get_current_weather(location: str) -> str:
    """Get the current weather for a location. Use 'auto' for saved location."""
    if not location or location == "auto":
        memory_data = load_memory()
        personal = memory_data.get("personal", {})
        location = (
            personal.get("location")
            or personal.get("current_residence")
            or personal.get("hometown")
        )

    if not location:
        return "I don't know your location. Please tell me where you are."

    data = get_weather(location)
    if not data:
        return f"Couldn't fetch weather for {location}"

    return (
        f"Weather in {data['city']}, {data['country']}: "
        f"{data['temp']}C (feels like {data['feels_like']}C), "
        f"{data['description']}, humidity {data['humidity']}%, "
        f"wind {data['wind']}m/s"
    )


@tool
def get_weather_forecast(query: str) -> str:
    """Get forecast for a location using the format 'location|target'."""
    try:
        parts = query.split("|")
        location = parts[0].strip() if parts and parts[0].strip() else "auto"
        target = parts[1].strip().lower() if len(parts) > 1 else "tomorrow"

        if not location or location == "auto":
            memory_data = load_memory()
            personal = memory_data.get("personal", {})
            location = (
                personal.get("location")
                or personal.get("current_residence")
                or personal.get("hometown")
            )

        if not location:
            return "I don't know your location. Please tell me where you are."

        if target == "tomorrow":
            data = get_tomorrow_forecast(location)
            if not data:
                return "Couldn't fetch tomorrow's forecast"
            return (
                f"Tomorrow ({data['day']}) in {data['city']}: "
                f"{data['min_temp']}C - {data['max_temp']}C, "
                f"{data['description']}, humidity {data['humidity']}%"
            )

        if target == "week":
            forecasts = get_forecast(location, days=5)
            if not forecasts:
                return "Couldn't fetch weekly forecast"
            lines = [
                f"{day['day']}: {day['min_temp']}C - {day['max_temp']}C, {day['description']}"
                for day in forecasts
            ]
            return f"5-day forecast for {forecasts[0]['city']}:\n" + "\n".join(lines)

        if target == "weekend":
            forecasts = get_forecast(location, days=5)
            if not forecasts:
                return "Couldn't fetch weekend forecast"
            weekend = [day for day in forecasts if day["day"] in ["Saturday", "Sunday"]]
            if not weekend:
                return "No weekend data in forecast range"
            lines = [
                f"{day['day']}: {day['min_temp']}C - {day['max_temp']}C, {day['description']}"
                for day in weekend
            ]
            return f"Weekend forecast for {forecasts[0]['city']}:\n" + "\n".join(lines)

        data = get_day_forecast(location, target)
        if not data:
            return f"No forecast found for {target}"

        return (
            f"{data['day']} in {data['city']}: "
            f"{data['min_temp']}C - {data['max_temp']}C, "
            f"{data['description']}, humidity {data['humidity']}%"
        )
    except Exception as exc:
        return f"Forecast error: {exc}"


@tool
def open_application(app_name: str) -> str:
    """Open an application on the computer and stop after that single action."""
    app_name = app_name.lower().strip()

    if open_app(app_name):
        time.sleep(2)
        app_process_names = {
            "chrome": "chrome.exe",
            "spotify": "Spotify.exe",
            "notepad": "notepad.exe",
            "calculator": "calculator.exe",
            "vscode": "code.exe",
            "file explorer": "explorer.exe",
        }
        process_name = app_process_names.get(app_name)
        if process_name:
            for proc in psutil.process_iter(["name"]):
                try:
                    if proc.info["name"] == process_name:
                        return f"DONE: {app_name} is now open successfully."
                except Exception:
                    pass
            return f"DONE: {app_name} launch was requested but could not verify."
        return f"DONE: {app_name} is now open."

    return f"DONE: Could not open {app_name}."


@tool
def close_application(app_name: str) -> str:
    """Close a running application on the computer."""
    from apps import close_app

    if close_app(app_name):
        return f"Closing {app_name}"
    return f"Couldn't close {app_name}"


@tool
def spotify_play_song(song_name: str) -> str:
    """Play a specific song on Spotify."""
    from spotify import play_song

    return play_song(song_name)


@tool
def spotify_play_playlist(playlist_name: str) -> str:
    """Play a specific playlist on Spotify."""
    from spotify import play_playlist

    return play_playlist(playlist_name)


@tool
def spotify_control(action: str) -> str:
    """Control Spotify playback with pause, resume, next, or previous."""
    from spotify import next_song, pause_music, previous_song, resume_music

    actions = {
        "pause": pause_music,
        "resume": resume_music,
        "next": next_song,
        "previous": previous_song,
    }
    func = actions.get(action.lower().strip())
    if func:
        return func()
    return f"Unknown action: {action}"


@tool
def save_memory(info: str) -> str:
    """Save long-term memory using the format 'category|key|value'."""
    try:
        parts = info.split("|")
        if len(parts) != 3:
            return "Invalid format - use 'category|key|value'"

        category, key, value = parts
        mem = load_memory()
        category = category.strip()
        key = key.strip()
        value = value.strip()

        if category not in mem:
            mem[category] = {}

        mem[category][key] = value
        memory_save(mem)

        # Keep semantic memory aligned with the exact structured fact we just saved.
        sync_structured_memory()
        print(f"Memory saved: [{category}] {key} = {value}")
        return f"Remembered: {key} = {value}"
    except Exception as exc:
        return f"Memory save failed: {exc}"


tools = [
    search_web,
    get_current_weather,
    get_weather_forecast,
    open_application,
    close_application,
    spotify_play_song,
    spotify_play_playlist,
    spotify_control,
    save_memory,
]

TOOLS_BY_NAME = {tool_item.name: tool_item for tool_item in tools}


def get_time_context() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "morning"
    if hour < 14:
        return "afternoon"
    if hour < 19:
        return "evening"
    return "night"


def get_recent_chat_messages(limit: int = 10):
    clean_history = [
        msg for msg in chat_history.messages if isinstance(msg, (HumanMessage, AIMessage))
    ]
    return clean_history[-limit:]


def build_chat_system_prompt(user_query: str, tool_result: str = "", reply_intent: str = "") -> str:
    memory_text = get_memory_text()
    semantic_memory_text = (
        get_semantic_memory_context(user_query) if user_query else "No relevant semantic memories found."
    )
    fresh_result = tool_result or "No fresh tool result for this turn."
    current_goal = reply_intent or user_query or "Answer naturally."

    return f"""You are Arfy, Senaa's personal AI assistant.
Current time of day: {get_time_context()}

Structured facts you know about Senaa:
{memory_text}

Relevant memories for this request:
{semantic_memory_text}

Current turn goal:
{current_goal}

Fresh tool result for this turn:
{fresh_result}

Response rules:
- Keep answers short, helpful, and conversational.
- If a fresh tool result is provided, use it as the main source for current facts.
- If the fresh tool result contains an error, explain the problem simply.
- Do not mention tools, prompts, routing, or internal reasoning.
- Never say that you called a tool.
"""


def extract_json_object(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("Router returned no JSON object.")
    return json.loads(match.group(0))


def fallback_route(question: str) -> RouteDecision:
    lower_question = question.lower()

    if any(word in lower_question for word in ["latest", "news", "war", "update", "current event", "who is"]):
        return RouteDecision(
            action="search_web",
            tool_input=question.strip(),
            reply_intent="Look up current information on the web",
        )

    if any(word in lower_question for word in ["weather", "temperature", "forecast", "rain", "sunny", "humid"]):
        if any(word in lower_question for word in ["tomorrow", "weekend", "week", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
            return RouteDecision(
                action="get_weather_forecast",
                tool_input="auto|tomorrow",
                reply_intent="Get a weather forecast",
            )
        return RouteDecision(
            action="get_current_weather",
            tool_input="auto",
            reply_intent="Get current weather",
        )

    return RouteDecision(action="chat", tool_input="", reply_intent="Answer normally")


def classify_request(question: str) -> RouteDecision:
    messages = [
        SystemMessage(content=ROUTER_PROMPT),
        HumanMessage(content=question),
    ]

    try:
        response = llm_router.invoke(messages)
        data = extract_json_object(response.content)
        decision = RouteDecision.model_validate(data)
        decision.tool_input = decision.tool_input.strip()
        decision.reply_intent = decision.reply_intent.strip() or question.strip()
        return decision
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        print(f"Router parse fallback: {exc}")
        return fallback_route(question)
    except Exception as exc:
        print(f"Router model fallback: {exc}")
        return fallback_route(question)


def build_fallback_tool_args(tool_name: str, tool_input: str, question: str) -> dict:
    normalized_input = tool_input.strip()

    if tool_name == "search_web":
        return {"query": normalized_input or question}
    if tool_name == "get_current_weather":
        return {"location": normalized_input or "auto"}
    if tool_name == "get_weather_forecast":
        return {"query": normalized_input or "auto|tomorrow"}
    if tool_name == "save_memory":
        return {"info": normalized_input}

    return {}


def merge_tool_args(tool_name: str, model_args: dict, tool_input: str, question: str) -> dict:
    merged = build_fallback_tool_args(tool_name, tool_input, question)

    for key, value in (model_args or {}).items():
        if value not in (None, ""):
            merged[key] = value

    return merged


def run_single_tool_call(question: str, decision: RouteDecision) -> str:
    tool_name = decision.action
    tool_item = TOOLS_BY_NAME[tool_name]
    forced_tool_llm = llm_tool.bind_tools(
        [tool_item],
        tool_choice={"type": "function", "function": {"name": tool_name}},
    )

    prompt_variants = [
        [
            SystemMessage(content=TOOL_CALLER_PROMPT),
            HumanMessage(
                content=(
                    f"User question:\n{question}\n\n"
                    f"Normalized tool input:\n{decision.tool_input or 'Use the user question directly.'}"
                )
            ),
        ],
        [
            SystemMessage(
                content=(
                    "Call the single provided tool exactly once. "
                    "Do not output plain text, XML, markdown, or pseudo-function tags."
                )
            ),
            HumanMessage(content=decision.tool_input or question),
        ],
    ]

    last_error = None

    # A single-tool retry path keeps the LLM involved but removes most formatting noise.
    for messages in prompt_variants:
        try:
            response = forced_tool_llm.invoke(messages)
            tool_calls = getattr(response, "tool_calls", None) or []
            if not tool_calls:
                raise RuntimeError("Tool caller returned no tool call.")

            tool_call = tool_calls[0]
            tool_args = merge_tool_args(
                tool_name,
                tool_call.get("args") or {},
                decision.tool_input,
                question,
            )
            result = tool_item.invoke(tool_args)
            return result if isinstance(result, str) else str(result)
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"Tool call failed for {tool_name}: {last_error}")


def generate_chat_response(question: str, tool_result: str = "", reply_intent: str = "") -> str:
    messages = [
        SystemMessage(content=build_chat_system_prompt(question, tool_result, reply_intent)),
        *get_recent_chat_messages(),
        HumanMessage(content=question),
    ]
    response = llm_chat.invoke(messages)
    return response.content.strip()


def ask_brain(question: str) -> str:
    try:
        # Sync structured facts before each turn so semantic retrieval stays fresh.
        sync_structured_memory()

        decision = classify_request(question)
        print(f"[LLM Router] action={decision.action} tool_input={decision.tool_input}")

        tool_result = ""
        if decision.action != "chat":
            tool_result = run_single_tool_call(question, decision)

        answer = generate_chat_response(
            question,
            tool_result=tool_result,
            reply_intent=decision.reply_intent,
        )

        chat_history.add_user_message(question)
        chat_history.add_ai_message(answer)

        if len(chat_history.messages) > 20:
            chat_history.messages = chat_history.messages[-20:]

        return answer
    except Exception as exc:
        print(f"Brain error: {exc}")
        return "Sorry, I had trouble processing that."

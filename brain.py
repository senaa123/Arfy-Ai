import os
import psutil
import time
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_community.tools import DuckDuckGoSearchRun
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.prebuilt import ToolNode

from memory import get_memory_text, load_memory, memory_save
from weather import (get_weather, get_forecast, get_tomorrow_forecast,
                     get_day_forecast)
from apps import open_app
    


# Init LLM - groq

llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.3-70b-versatile",
    temperature=0.4,
    max_tokens=200
)

# conversation history
chat_history = ChatMessageHistory()


# TOOLS

@tool
def search_web(query: str) -> str:
    """Search the web for current news, events or any real time information."""
    try:
        search = DuckDuckGoSearchRun()
        return search.run(query)
    except Exception as e:
        return f"Search failed: {e}"

@tool
def get_current_weather(location: str) -> str:
    """Get the current weather for a location. Use 'auto' to use Senaa's saved location."""
    if not location or location == "auto":
        memory_data = load_memory()
        personal = memory_data.get("personal", {})
        location = (personal.get("location") or
                    personal.get("current_residence") or
                    personal.get("hometown"))
    if not location:
        return "I don't know your location. Please tell me where you are."
    data = get_weather(location)
    if not data:
        return f"Couldn't fetch weather for {location}"
    return (f"Weather in {data['city']}, {data['country']}: "
            f"{data['temp']}°C (feels like {data['feels_like']}°C), "
            f"{data['description']}, humidity {data['humidity']}%, "
            f"wind {data['wind']}m/s")

@tool
def get_weather_forecast(query: str) -> str:
    """Get weather forecast for a location.
    Query format: 'location|target'
    Target options: tomorrow, week, weekend, monday, tuesday, wednesday, thursday, friday, saturday, sunday
    Use 'auto' as location to use Senaa's saved location.
    Example: 'Colombo|tomorrow' or 'auto|week' or 'auto|saturday'
    """
    try:
        parts = query.split("|")
        location = parts[0].strip() if parts[0].strip() else "auto"
        target = parts[1].strip().lower() if len(parts) > 1 else "tomorrow"

        if not location or location == "auto":
            memory_data = load_memory()
            personal = memory_data.get("personal", {})
            location = (personal.get("location") or
                        personal.get("current_residence") or
                        personal.get("hometown"))

        if not location:
            return "I don't know your location. Please tell me where you are."

        if target == "tomorrow":
            data = get_tomorrow_forecast(location)
            if not data:
                return "Couldn't fetch tomorrow's forecast"
            return (f"Tomorrow ({data['day']}) in {data['city']}: "
                    f"{data['min_temp']}°C - {data['max_temp']}°C, "
                    f"{data['description']}, humidity {data['humidity']}%")

        elif target == "week":
            forecasts = get_forecast(location, days=5)
            if not forecasts:
                return "Couldn't fetch weekly forecast"
            result = f"5-day forecast for {forecasts[0]['city']}:\n"
            for day in forecasts:
                result += f"{day['day']}: {day['min_temp']}°C - {day['max_temp']}°C, {day['description']}\n"
            return result

        elif target == "weekend":
            forecasts = get_forecast(location, days=5)
            if not forecasts:
                return "Couldn't fetch weekend forecast"
            weekend = [d for d in forecasts if d["day"] in ["Saturday", "Sunday"]]
            if not weekend:
                return "No weekend data in forecast range"
            result = f"Weekend forecast for {forecasts[0]['city']}:\n"
            for day in weekend:
                result += f"{day['day']}: {day['min_temp']}°C - {day['max_temp']}°C, {day['description']}\n"
            return result

        else:
            data = get_day_forecast(location, target)
            if not data:
                return f"No forecast found for {target} — may be outside 5 day range"
            return (f"{data['day']} in {data['city']}: "
                    f"{data['min_temp']}°C - {data['max_temp']}°C, "
                    f"{data['description']}, humidity {data['humidity']}%")

    except Exception as e:
        return f"Forecast error: {e}"

@tool
def open_application(app_name: str) -> str:
    """Open an application on the computer.
    Available apps: chrome, spotify, notepad, calculator, vscode, file explorer
    ONLY opens the app — does NOT play music or do anything else.
    Returns DONE when complete — do not call any other tools after this."""
    

    app_name = app_name.lower().strip()

    if open_app(app_name):
        # verify it actually opened by checking process
        time.sleep(2)
        app_process_names = {
            "chrome": "chrome.exe",
            "spotify": "Spotify.exe",
            "notepad": "notepad.exe",
            "calculator": "calculator.exe",
            "vscode": "code.exe",
            "file explorer": "explorer.exe"
        }
        process_name = app_process_names.get(app_name)
        if process_name:
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] == process_name:
                        return f"DONE: {app_name} is now open successfully."
                except:
                    pass
            return f"DONE: {app_name} launch was requested but could not verify."
        return f"DONE: {app_name} is now open."
    return f"DONE: Could not open {app_name}."

@tool
def close_application(app_name: str) -> str:
    """Close a running application on the computer.
    ONLY call this when the user EXPLICITLY says close or shut down.
    Do NOT call this to fix errors."""
    from apps import close_app
    if close_app(app_name):
        return f"Closing {app_name}"
    return f"Couldn't close {app_name}"

@tool
def spotify_play_song(song_name: str) -> str:
    """Play a specific song on Spotify.
    This will open Spotify automatically if not open."""
    from spotify import play_song
    return play_song(song_name)

@tool
def spotify_play_playlist(playlist_name: str) -> str:
    """Play a specific playlist on Spotify.
    This will open Spotify automatically if not open."""
    from spotify import play_playlist
    return play_playlist(playlist_name)

@tool
def spotify_control(action: str) -> str:
    """Control Spotify playback.
    Actions: pause, resume, next, previous"""
    from spotify import pause_music, resume_music, next_song, previous_song
    actions = {
        "pause": pause_music,
        "resume": resume_music,
        "next": next_song,
        "previous": previous_song
    }
    func = actions.get(action.lower().strip())
    if func:
        return func()
    return f"Unknown action: {action}"

@tool
def save_memory(info: str) -> str:
    """Save important long term information about Senaa to memory.
    Format: 'category|key|value'
    Categories: personal, preferences, facts
    Example: 'personal|job|software engineer'
    Only save permanent facts — NOT temporary things like mood."""
    try:
        parts = info.split("|")
        if len(parts) != 3:
            return "Invalid format — use 'category|key|value'"
        category, key, value = parts
        mem = load_memory()
        if category.strip() not in mem:
            mem[category.strip()] = {}
        mem[category.strip()][key.strip()] = value.strip()
        memory_save(mem)
        print(f"Memory saved: [{category}] {key} = {value}")
        return f"Remembered: {key.strip()} = {value.strip()}"
    except Exception as e:
        return f"Memory save failed: {e}"

# ─────────────────────────────────────────
# TOOLS LIST
# ─────────────────────────────────────────

tools = [
    search_web,
    get_current_weather,
    get_weather_forecast,
    open_application,
    close_application,
    spotify_play_song,
    spotify_play_playlist,
    spotify_control,
    save_memory
]

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def get_time_context():
    hour = datetime.now().hour
    if hour < 12:
        return "morning"
    elif hour < 14:
        return "afternoon"
    elif hour < 19:
        return "evening"
    else:
        return "night"

def get_system_prompt():
    memory_text = get_memory_text()
    return f"""You are Arfy, Senaa's personal AI assistant.
Current time of day: {get_time_context()}

What you know about Senaa:
{memory_text}

STRICT RULES — FOLLOW THESE EXACTLY:
1. Only do EXACTLY what the user asks. Nothing more, nothing less.
2. NEVER call more than 1 tool unless the user explicitly asks for multiple things.
3. NEVER retry a tool if it returns an error — just report the error to the user.
4. NEVER call close_application unless the user explicitly says "close" or "shut down".
5. NEVER assume the user wants music played just because Spotify is mentioned.
6. NEVER chain tools on your own — wait for the user to ask.
7. If a tool returns a 404 or device error — tell the user, do NOT call other tools.
8. If spotify says "taking too long to connect" — tell user to click play in Spotify manually.
9 When a tool returns a message starting with DONE — stop immediately and report to user.
10 Do NOT call any more tools after seeing DONE.
11 Do NOT try to verify or re-check after DONE.

TOOL USAGE RULES:
- "open spotify" → ONLY call open_application. Do NOT call spotify tools.
- "play a song" → call spotify_play_song. It will open Spotify automatically.
- "play a playlist" → call spotify_play_playlist. It will open Spotify automatically.
- "pause / resume / next / previous" → call spotify_control only.
- "open chrome / notepad / vscode" → ONLY call open_application.
- "close X" → ONLY call close_application when user explicitly says close.
- "weather" → call get_current_weather or get_weather_forecast.
- "news / latest / who is" → call search_web.
- "remember this" → call save_memory.

RESPONSE RULES:
- Keep responses short and conversational.
- NEVER say "I've called the tool" or "I'm calling the tool" — just do it and report the result.
- Never repeat what tool you called — just give the result naturally.
- If something failed — say it simply and suggest what to do.
- Talk like a friendly personal assistant, not a robot.
- Never reference previous tool calls in your response.

MEMORY RULES:
- If you learn something NEW and IMPORTANT about Senaa use save_memory tool.
- Only save long term facts like job, location, hobbies, preferences.
- Do NOT save temporary things like mood or current activity."""

# ─────────────────────────────────────────
# STATE GRAPH AGENT
# ─────────────────────────────────────────

# bind tools to llm
llm_with_tools = llm.bind_tools(tools)

def agent_node(state: MessagesState):
    """LLM decides what to do"""
    system = SystemMessage(content=get_system_prompt())
    messages = [system] + state["messages"]
    response = llm_with_tools.invoke(messages)

    # prevent multiple tool calls
    if hasattr(response, "tool_calls") and len(response.tool_calls) > 1:
        response.tool_calls = response.tool_calls[:1]
    return {"messages": [response]}

def should_continue(state: MessagesState):
    """Check if we should call tools or stop."""

    last_message = state["messages"][-1]

    # If the LLM requested a tool → run tools
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    # If the last message is from a tool → STOP
    if hasattr(last_message, "type") and last_message.type == "tool":
        return END

    # Otherwise stop
    return END

# tool node handles all tool execution
tool_node = ToolNode(tools)

def build_graph():
    graph = StateGraph(MessagesState)

    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)

    graph.set_entry_point("agent")

    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END
        }
    )

    # END after tool
    graph.add_edge("tools", END)

    return graph.compile()
# build graph once
graph = build_graph()

# ─────────────────────────────────────────
# MAIN FUNCTION
# ─────────────────────────────────────────

def ask_brain(question: str) -> str:
    try:
        # only keep human and AI messages in history — not tool messages
        clean_history = [
            msg for msg in chat_history.messages
            if isinstance(msg, (HumanMessage, AIMessage))
        ]

        messages = clean_history[-10:] + [HumanMessage(content=question)]

        result = graph.invoke(
            {"messages": messages},
            config={"recursion_limit": 8}
        )

        answer = result["messages"][-1].content

        # only save clean human/AI messages
        chat_history.add_user_message(question)
        chat_history.add_ai_message(answer)

        if len(chat_history.messages) > 20:
            chat_history.messages = chat_history.messages[-20:]

        return answer

    except Exception as e:
        print(f"Brain error: {e}")
        return "Sorry, I had trouble processing that."
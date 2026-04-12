import queue
import sys
import threading
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

from PyQt6.QtCore import Q_ARG, QMetaObject, Qt
from PyQt6.QtWidgets import QApplication

from Ui.main_window import ArfyWindow
from Ui.tray import ArfyTray
from action_executor import execute_action
from agent_client import ask_agent, agent_health_check, end_agent_session
from intent_router import route_local_intent
from memory_client import log_action, memory_health_check, retrieve_memory
from speech import listen
from tts_engine import speak
from wakeword import wait_for_wake_word

typed_queue = queue.Queue()
input_mode = False

# Current live wake-session id.
# A new one is created every time Arfy wakes up.
CURRENT_SESSION_ID: str | None = None


def create_session_id() -> str:
    """
    Create a unique session id for each wake cycle.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_part = uuid.uuid4().hex[:8]
    return f"arfy_{timestamp}_{random_part}"


# -------------------------
# NEW: local system status check
# -------------------------
def handle_system_status_command(text: str) -> bool:
    """
    Handle explicit local system status requests.

    This is intentionally NOT routed through the agent.
    That keeps service checks out of normal conversation flow.
    """
    lower = text.lower().strip()

    trigger_phrases = [
        "check system status",
        "system status",
        "health check",
        "check the system status",
        "check status",
        "status report",
        "system report",
        "report of the system",
    ]

    keyword_match = (
        "system" in lower
        and ("status" in lower or "health" in lower or "report" in lower)
    )

    if not any(phrase in lower for phrase in trigger_phrases) and not keyword_match:
        return False

    agent_ok = agent_health_check()
    memory_ok = memory_health_check()

    report_lines = [
        "System status report.",
        f"Agent service: {'working' if agent_ok else 'not reachable'}.",
        f"Memory service: {'working' if memory_ok else 'not reachable'}.",
    ]

    response = " ".join(report_lines)

    print(response)
    ui_chat("Arfy", response)
    ui_state("speaking")
    speak(response)
    ui_state("listening" if not input_mode else "idle")

    return True


# -------------------------
# UI helper functions
# -------------------------
def ui_state(state):
    QMetaObject.invokeMethod(
        window,
        "set_state",
        Qt.ConnectionType.QueuedConnection,
        Q_ARG(str, state),
    )


def ui_chat(sender, message):
    QMetaObject.invokeMethod(
        window,
        "add_chat",
        Qt.ConnectionType.QueuedConnection,
        Q_ARG(str, sender),
        Q_ARG(str, message),
    )


def ui_show_input():
    QMetaObject.invokeMethod(
        window,
        "show_input",
        Qt.ConnectionType.QueuedConnection,
    )


def ui_hide_input():
    QMetaObject.invokeMethod(
        window,
        "hide_input",
        Qt.ConnectionType.QueuedConnection,
    )


def ui_set_mode_label(mode):
    QMetaObject.invokeMethod(
        window,
        "set_mode_label",
        Qt.ConnectionType.QueuedConnection,
        Q_ARG(str, mode),
    )


# -------------------------
# Input handling
# -------------------------
def get_input():
    """
    If in input mode, wait for typed text from the UI.
    Otherwise use voice input.
    """
    global input_mode

    if input_mode:
        try:
            return typed_queue.get(timeout=60)
        except queue.Empty:
            return None
    else:
        return listen(time_limit=6)


def finalize_current_session():
    """
    End the current session cleanly.
    """
    global CURRENT_SESSION_ID

    if not CURRENT_SESSION_ID:
        return

    result = end_agent_session(CURRENT_SESSION_ID)
    print(f"Session ended: {CURRENT_SESSION_ID}")
    print(f"Session archive result: {result}")

    CURRENT_SESSION_ID = None


# -------------------------
# Local desktop-only commands
# -------------------------
def handle_local_command(command: str):
    """
    Handle desktop-local commands that do not need the LLM.
    """
    global input_mode

    if command == "switch_input_mode":
        input_mode = True
        ui_show_input()
        ui_set_mode_label("INPUT MODE")
        ui_state("speaking")
        speak("Switching to input mode!")
        ui_state("idle")
        return True

    if command == "switch_voice_mode":
        input_mode = False
        ui_hide_input()
        ui_set_mode_label("VOICE MODE")
        ui_state("speaking")
        speak("Switching to voice mode!")
        ui_state("listening")
        return True

    if command == "goodbye":
        input_mode = False
        ui_hide_input()
        ui_set_mode_label("VOICE MODE")

        finalize_current_session()

        ui_state("speaking")
        ui_chat("Arfy", "Goodbye Senaa!")
        speak("Goodbye Senaa!")
        ui_state("idle")
        return False

    if command == "shutdown":
        finalize_current_session()

        ui_state("speaking")
        speak("Shutting down! Bye Senaa!")
        app.quit()
        return False

    return True


# -------------------------
# Main command handling
# -------------------------
def handle_command(text):
    """
    Handle one user utterance during an active wake session.
    """
    global input_mode, CURRENT_SESSION_ID

    if not text:
        return True

    if not CURRENT_SESSION_ID:
        CURRENT_SESSION_ID = create_session_id()

    normalized_text = text.strip().lower()

    if any(phrase in normalized_text for phrase in ["switch to input mode", "input mode"]):
        return handle_local_command("switch_input_mode")

    if any(phrase in normalized_text for phrase in ["switch to voice mode", "voice mode"]):
        return handle_local_command("switch_voice_mode")

    if any(phrase in normalized_text for phrase in ["let me type", "i'll type", "let me write"]):
        ui_state("speaking")
        speak("Sure, go ahead and type!")
        ui_show_input()
        ui_state("idle")

        try:
            text = typed_queue.get(timeout=30)
            normalized_text = text.strip().lower()
            ui_hide_input()
        except queue.Empty:
            ui_hide_input()
            speak("You didn't type anything.")
            return True

    ui_chat("You", text)

    if any(word in normalized_text for word in ["goodbye", "sleep", "seeyou"]):
        return handle_local_command("goodbye")

    if any(word in normalized_text for word in ["stop", "exit", "quit"]):
        return handle_local_command("shutdown")

    # NEW:
    # Run local system status check only when explicitly requested.
    if handle_system_status_command(text):
        return True

    local_result = route_local_intent(normalized_text)
    if local_result is not None:
        command = local_result.get("command")
        return handle_local_command(command)

    ui_state("thinking")

    memories = retrieve_memory(normalized_text, limit=5)

    result = ask_agent(
        text=normalized_text,
        session_id=CURRENT_SESSION_ID,
        memories=memories,
    )

    response = result.get("response", "Sorry, I couldn't reach the agent service.")
    action = result.get("action")

    # Debug prints are useful while testing
    print("USER TEXT:", normalized_text)
    print("AGENT RESULT:", result)
    print("ACTION FROM AGENT:", action)

    if action:
        success, action_message = execute_action(action)

        log_action(
            action=str(action),
            action_type=action.get("type", "unknown"),
            success=success,
        )

        print(action_message)

        # For normal actions, only replace spoken reply if execution failed.
        if not success:
            response = action_message

    ui_state("speaking")
    print(f"Arfy [{CURRENT_SESSION_ID}]: {response}")
    ui_chat("Arfy", response)
    speak(response)

    ui_state("listening" if not input_mode else "idle")
    return True


# -------------------------
# Main assistant loop
# -------------------------
def arfy_loop():
    """
    Main wake-loop for Arfy.
    """
    global input_mode, CURRENT_SESSION_ID

    if not agent_health_check():
        print("⚠️ Agent service not running")
        speak("Warning! Agent service is not running.")

    if not memory_health_check():
        print("⚠️ Memory service not running")
        speak("Warning! Memory service is not running.")

    ui_state("speaking")
    speak("Hello! I am Arfy, your personal assistant!")
    ui_state("idle")

    while True:
        result = wait_for_wake_word()

        if result == "shutdown":
            finalize_current_session()
            ui_state("speaking")
            speak("Shutting down! Bye Senaa!")
            app.quit()
            return

        elif result == "wake":
            CURRENT_SESSION_ID = create_session_id()
            print(f"New session started: {CURRENT_SESSION_ID}")

            ui_state("speaking")
            speak("Yes Senaa!")
            ui_state("listening")

            active_chat = True

            while active_chat:
                ui_state("idle" if input_mode else "listening")

                text = get_input()
                if not text:
                    continue

                active_chat = handle_command(text)


app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

window = ArfyWindow()
window.show()

tray = ArfyTray(window)

window.text_submitted.connect(lambda text: typed_queue.put(text))

arfy_thread = threading.Thread(target=arfy_loop, daemon=True)
arfy_thread.start()

sys.exit(app.exec())

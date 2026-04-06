import sys
import threading
import queue
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QMetaObject, Qt, Q_ARG

from Ui.main_window import ArfyWindow
from Ui.tray import ArfyTray

from speech import listen_with_type_fallback
from wakeword import wait_for_wake_word
from tts_engine import speak
from intent_router import route_local_intent
from agent_client import ask_agent, agent_health_check
from action_executor import execute_action
from memory_client import (
    retrieve_memory,
    log_action,
    memory_health_check,
)

# Session id for short-term history in agent service
SESSION_ID = "senaa_01"

typed_queue = queue.Queue()
input_mode = False


# -------------------------
# UI helper functions
# -------------------------
def ui_state(state):
    QMetaObject.invokeMethod(
        window,
        "set_state",
        Qt.ConnectionType.QueuedConnection,
        Q_ARG(str, state)
    )


def ui_chat(sender, message):
    QMetaObject.invokeMethod(
        window,
        "add_chat",
        Qt.ConnectionType.QueuedConnection,
        Q_ARG(str, sender),
        Q_ARG(str, message)
    )


def ui_show_input():
    QMetaObject.invokeMethod(
        window,
        "show_input",
        Qt.ConnectionType.QueuedConnection
    )


def ui_hide_input():
    QMetaObject.invokeMethod(
        window,
        "hide_input",
        Qt.ConnectionType.QueuedConnection
    )


def ui_set_mode_label(mode):
    QMetaObject.invokeMethod(
        window,
        "set_mode_label",
        Qt.ConnectionType.QueuedConnection,
        Q_ARG(str, mode)
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
        return listen_with_type_fallback()


# -------------------------
# Local desktop-only commands
# -------------------------
def handle_local_command(command: str):
    """
    Handle tiny fast desktop-only commands without asking agent service.
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
        ui_state("speaking")
        ui_chat("Arfy", "Goodbye Senaa!")
        speak("Goodbye Senaa!")
        ui_state("idle")
        return False

    if command == "shutdown":
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
    Main desktop-side command flow:
    1. handle local commands first
    2. retrieve relevant memories
    3. ask agent service
    4. execute returned action if any
    5. log executed action
    6. speak response
    """
    global input_mode

    if not text:
        return True

    normalized_text = text.strip().lower()

    # -------------------------
    # Local mode switches
    # -------------------------
    if any(phrase in normalized_text for phrase in ["switch to input mode", "input mode"]):
        return handle_local_command("switch_input_mode")

    if any(phrase in normalized_text for phrase in ["switch to voice mode", "voice mode"]):
        return handle_local_command("switch_voice_mode")

    # -------------------------
    # One-time typed input
    # -------------------------
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

    # -------------------------
    # Local goodbye / shutdown
    # -------------------------
    if any(word in normalized_text for word in ["goodbye", "sleep", "seeyou"]):
        return handle_local_command("goodbye")

    if any(word in normalized_text for word in ["stop", "exit", "quit"]):
        return handle_local_command("shutdown")

    # -------------------------
    # Tiny local router only
    # -------------------------
    local_result = route_local_intent(normalized_text)
    if local_result is not None:
        command = local_result.get("command")
        return handle_local_command(command)

    # -------------------------
    # Ask memory service first
    # -------------------------
    ui_state("thinking")
    memories = retrieve_memory(normalized_text, limit=5)

    # -------------------------
    # Ask agent service
    # -------------------------
    result = ask_agent(
        text=normalized_text,
        session_id=SESSION_ID,
        memories=memories
    )

    response = result.get("response", "Sorry, I couldn't reach the agent service.")
    action = result.get("action")

    # -------------------------
    # Execute action if returned
    # -------------------------
    if action:
        success, action_message = execute_action(action)

        log_action(
            action=str(action),
            action_type=action.get("type", "unknown"),
            success=success
        )

        print(action_message)

        # Do not let Arfy claim success when the action failed
        if not success:
            response = action_message

    # -------------------------
    # Speak + show response
    # -------------------------
    ui_state("speaking")
    print(f"Arfy: {response}")
    ui_chat("Arfy", response)
    speak(response)

    ui_state("listening" if not input_mode else "idle")
    return True


# -------------------------
# Main assistant loop
# -------------------------
def arfy_loop():
    global input_mode

    # Startup checks
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
            ui_state("speaking")
            speak("Shutting down! Bye Senaa!")
            app.quit()
            return

        elif result == "wake":
            ui_state("speaking")
            speak("Yes Senaa!")
            ui_state("listening")
            active_chat = True

            while active_chat:
                if input_mode:
                    ui_state("idle")
                else:
                    ui_state("listening")

                text = get_input()
                if not text:
                    continue

                active_chat = handle_command(text)


# -------------------------
# Startup
# -------------------------
app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

window = ArfyWindow()
window.show()

tray = ArfyTray(window)

window.text_submitted.connect(lambda text: typed_queue.put(text))

arfy_thread = threading.Thread(target=arfy_loop, daemon=True)
arfy_thread.start()

sys.exit(app.exec())
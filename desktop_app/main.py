import sys
import threading
import queue
from dotenv import load_dotenv
load_dotenv()

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
from Ui.main_window import ArfyWindow
from Ui.tray import ArfyTray

from speech import listen, listen_with_type_fallback
from wakeword import wait_for_wake_word
from tts_engine import speak
from intent_router import route_intent
from agent_client import ask_agent, is_agent_alive
from action_executor import execute_action
from memory_client import save_memory, is_memory_alive 

typed_queue = queue.Queue()
input_mode = False

def ui_state(state):
    QMetaObject.invokeMethod(window, "set_state",
                             Qt.ConnectionType.QueuedConnection,
                             Q_ARG(str, state))

def ui_chat(sender, message):
    QMetaObject.invokeMethod(window, "add_chat",
                             Qt.ConnectionType.QueuedConnection,
                             Q_ARG(str, sender),
                             Q_ARG(str, message))

def ui_show_input():
    QMetaObject.invokeMethod(window, "show_input",
                             Qt.ConnectionType.QueuedConnection)

def ui_hide_input():
    QMetaObject.invokeMethod(window, "hide_input",
                             Qt.ConnectionType.QueuedConnection)

def ui_set_mode_label(mode):
    QMetaObject.invokeMethod(window, "set_mode_label",
                             Qt.ConnectionType.QueuedConnection,
                             Q_ARG(str, mode))

def get_input():
    global input_mode
    if input_mode:
        try:
            return typed_queue.get(timeout=60)
        except queue.Empty:
            return None
    else:
        return listen_with_type_fallback()

def handle_command(text):
    global input_mode

    # mode switches
    if any(phrase in text for phrase in ["switch to input mode", "input mode"]):
        input_mode = True
        ui_show_input()
        ui_set_mode_label("INPUT MODE")
        ui_state("speaking")
        speak("Switching to input mode!")
        ui_state("idle")
        return True

    if any(phrase in text for phrase in ["switch to voice mode", "voice mode"]):
        input_mode = False
        ui_hide_input()
        ui_set_mode_label("VOICE MODE")
        ui_state("speaking")
        speak("Switching to voice mode!")
        ui_state("listening")
        return True

    # one time type
    if any(phrase in text for phrase in ["let me type", "i'll type", "let me write"]):
        ui_state("speaking")
        speak("Sure, go ahead and type!")
        ui_show_input()
        ui_state("idle")
        try:
            text = typed_queue.get(timeout=30)
            ui_hide_input()
        except queue.Empty:
            ui_hide_input()
            speak("You didn't type anything.")
            return True

    ui_chat("You", text)

    if any(phrase in text for phrase in ["remember", "save that", "don't forget"]):
        # extract what to remember
        # example: "remember I like rock music"
        ui_state("thinking")
        result = ask_agent(text)  # agent figures out what to save
        if result:
            response = result.get("response", "Got it!")
            action = result.get("action")
            # if agent returns a memory save action
            if action and action.get("type") == "save_memory":
                payload = action.get("payload", {})
                save_memory(
                    payload.get("category", "facts"),
                    payload.get("key", "note"),
                    payload.get("value", "")
                )

    # goodbye
    if any(word in text for word in ["goodbye", "sleep", "seeyou"]):
        input_mode = False
        ui_hide_input()
        ui_set_mode_label("VOICE MODE")
        ui_state("speaking")
        ui_chat("Arfy", "Goodbye Senaa!")
        speak("Goodbye Senaa!")
        ui_state("idle")
        return False

    # shutdown
    if any(word in text for word in ["stop", "exit", "quit"]):
        ui_state("speaking")
        speak("Shutting down! Bye Senaa!")
        app.quit()
        return False

    ui_state("thinking")

    # step 1 — local router first
    response = route_intent(text)
    action = None

    if response:
        print(f"[Router] Handled locally: {text}")
    else:
        # step 2 — send to agent service
        print(f"[Router] Sending to Agent: {text}")
        result = ask_agent(text)

        if result:
            response = result.get("response", "I had trouble with that.")
            action = result.get("action")
        else:
            response = "Sorry, I couldn't reach the agent service."

    # step 3 — execute action if returned
    if action:
        execute_action(action)

    ui_state("speaking")
    print(f"Arfy: {response}")
    ui_chat("Arfy", response)
    speak(response)
    ui_state("listening" if not input_mode else "idle")

    return True

def arfy_loop():
    global input_mode

    # check agent service on startup
    if not is_agent_alive():
        print("⚠️ Agent service not running at localhost:8001")
        speak("Warning! Agent service is not running.")
    if not is_memory_alive():  # memory check
        print("⚠️ Memory service not running at localhost:8002")
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

# ─────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────
app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

window = ArfyWindow()
window.show()
tray = ArfyTray(window)

window.text_submitted.connect(lambda text: typed_queue.put(text))

arfy_thread = threading.Thread(target=arfy_loop, daemon=True)
arfy_thread.start()

sys.exit(app.exec())
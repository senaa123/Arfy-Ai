import sys
import threading
import queue
from dotenv import load_dotenv
load_dotenv()

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
from Ui.main_window import ArfyWindow
from Ui.tray import ArfyTray

from speech import speak, listen, listen_with_type_fallback, wait_for_wake_word
from brain import ask_brain
from intent_router import route_intent

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
    if any(phrase in text for phrase in ["let me type", "i'll type", "let me write", "input field"]):
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

    # sleep setup
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

    # INTENT ROUTER FIRST
    ui_state("thinking")
    response = route_intent(text)

    if response:
        # handled locally — no LLM
        print(f"[Router] Handled: {text} → {response}")
    else:
        # not handled — send to LLM
        print(f"[Router] No match — sending to LLM: {text}")
        response = ask_brain(text)

    ui_state("speaking")
    print(f"Arfy: {response}")
    ui_chat("Arfy", response)
    speak(response)
    ui_state("listening" if not input_mode else "idle")

    return True

def arfy_loop():
    global input_mode

    ui_state("speaking")
    speak("Hello! I am Arfy, your personal assistant!")
    ui_state("idle")

    while True:
        if wait_for_wake_word():
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

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

window = ArfyWindow()
window.show()
tray = ArfyTray(window)

window.text_submitted.connect(lambda text: typed_queue.put(text))

arfy_thread = threading.Thread(target=arfy_loop, daemon=True)
arfy_thread.start()

sys.exit(app.exec())
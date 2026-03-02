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
from apps import open_app, close_app, parse_command
from brain import ask_brain
from spotify import play_song, pause_music, next_song, play_playlist, previous_song, resume_music

# queue for typed text from UI
typed_queue = queue.Queue()

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

def arfy_loop():
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
                ui_state("listening")
                text = listen_with_type_fallback()

                if not text:
                    continue

                # check if user wants to type
                if any(phrase in text for phrase in ["let me type", "i'll type", "let me write", "input field"]):
                    ui_state("speaking")
                    speak("Sure, go ahead and type!")
                    ui_show_input()

                    # wait for typed input from queue
                    ui_state("idle")
                    try:
                        text = typed_queue.get(timeout=30)
                    except queue.Empty:
                        ui_hide_input()
                        speak("You didn't type anything.")
                        continue

                ui_chat("You", text)

                if any(word in text for word in ["goodbye", "sleep", "seeyou"]):
                    ui_state("speaking")
                    ui_chat("Arfy", "Goodbye Senaa!")
                    speak("Goodbye Senaa!")
                    active_chat = False
                    ui_state("idle")
                    break

                if any(word in text for word in ["stop", "exit", "quit"]):
                    ui_state("speaking")
                    speak("Shutting down! Bye Senaa!")
                    app.quit()
                    return

                try:
                    command_type, data = parse_command(text)

                    if command_type == "open_app":
                        ui_state("thinking")
                        if not data:
                            response = "Which app do you want to open?"
                        elif open_app(data):
                            response = f"Opening {data}"
                        else:
                            response = f"Failed to open {data}"
                        ui_state("speaking")
                        ui_chat("Arfy", response)
                        speak(response)
                        ui_state("listening")

                    elif command_type == "close_app":
                        while True:
                            ui_state("speaking")
                            speak(f"Are you sure you want to close {data}?")
                            ui_state("listening")
                            text1 = listen(time_limit=8)
                            print(f"You said: {text1}")

                            if text1 and any(word in text1 for word in ["yes", "yeah", "yep", "correct"]):
                                ui_state("thinking")
                                if close_app(data):
                                    response = f"Closing {data}"
                                else:
                                    response = f"Failed to close {data}"
                                ui_state("speaking")
                                ui_chat("Arfy", response)
                                speak(response)
                                ui_state("listening")
                                break
                            elif text1 and any(word in text1 for word in ["no", "nah", "nope"]):
                                ui_state("speaking")
                                speak("Okay, not closing.")
                                ui_state("listening")
                                break
                            else:
                                ui_state("speaking")
                                speak("Please say yes or no.")
                                ui_state("listening")
                                continue

                    elif command_type == "play_song":
                        ui_state("thinking")
                        response = play_song(data)
                        ui_state("speaking")
                        ui_chat("Arfy", response)
                        speak(response)
                        ui_state("listening")

                    elif command_type == "play_playlist":
                        ui_state("thinking")
                        response = play_playlist(data)
                        ui_state("speaking")
                        ui_chat("Arfy", response)
                        speak(response)
                        ui_state("listening")

                    elif command_type == "pause_music":
                        ui_state("thinking")
                        response = pause_music()
                        ui_state("speaking")
                        ui_chat("Arfy", response)
                        speak(response)
                        ui_state("listening")

                    elif command_type == "resume_music":
                        ui_state("thinking")
                        response = resume_music()
                        ui_state("speaking")
                        ui_chat("Arfy", response)
                        speak(response)
                        ui_state("listening")

                    elif command_type == "next_song":
                        ui_state("thinking")
                        response = next_song()
                        ui_state("speaking")
                        ui_chat("Arfy", response)
                        speak(response)
                        ui_state("listening")

                    elif command_type == "previous_song":
                        ui_state("thinking")
                        response = previous_song()
                        ui_state("speaking")
                        ui_chat("Arfy", response)
                        speak(response)
                        ui_state("listening")

                    else:
                        ui_state("thinking")
                        response = ask_brain(data)
                        ui_state("speaking")
                        print(f"Arfy: {response}")
                        ui_chat("Arfy", response)
                        speak(response)
                        ui_state("listening")

                except Exception as e:
                    print(f"Error: {e}")
                    ui_state("speaking")
                    speak("Sorry, I had trouble processing that.")
                    ui_state("listening")

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

window = ArfyWindow()
window.show()
tray = ArfyTray(window)

# connect signal in main thread
window.text_submitted.connect(lambda text: typed_queue.put(text))

arfy_thread = threading.Thread(target=arfy_loop, daemon=True)
arfy_thread.start()

sys.exit(app.exec())
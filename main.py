import sys
import threading
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

def ui_state(state):
    QMetaObject.invokeMethod(window, "set_state", Qt.ConnectionType.QueuedConnection,
                             Q_ARG(str, state))

def ui_chat(sender, message):
    QMetaObject.invokeMethod(window, "add_chat",
                             Qt.ConnectionType.QueuedConnection,
                             Q_ARG(str, sender),
                             Q_ARG(str, message))
def arfy_loop():
    ui_state("idle")
    speak("Hello! I am Arfy, your personal assistant!")

    while True:
        if wait_for_wake_word():
            ui_state("listening")
            speak("Yes Senaa!")
            active_chat = True

            while active_chat:
                ui_state("listening")
                text = listen_with_type_fallback()

                if not text:
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
                    speak("Shutting down! Bye Senaa!")
                    app.quit()
                    return

                try:
                    command_type, data = parse_command(text)

                    if command_type == "open_app":
                        ui_state("speaking")
                        if not data:
                            response = "Which app do you want to open?"
                        elif open_app(data):
                            response = f"Opening {data}"
                        else:
                            response = f"Failed to open {data}"
                        ui_chat("Arfy", response)
                        speak(response)

                    elif command_type == "close_app":
                        while True:
                            ui_state("speaking")
                            speak(f"Are you sure you want to close {data}?")
                            ui_state("listening")
                            text1 = listen(time_limit=8)
                            print(f"You said: {text1}")

                            if text1 and any(word in text1 for word in ["yes", "yeah", "yep", "correct"]):
                                ui_state("speaking")
                                if close_app(data):
                                    response = f"Closing {data}"
                                else:
                                    response = f"Failed to close {data}"
                                ui_chat("Arfy", response)
                                speak(response)
                                break
                            elif text1 and any(word in text1 for word in ["no", "nah", "nope"]):
                                speak("Okay, not closing.")
                                break
                            else:
                                speak("Please say yes or no.")
                                continue

                    elif command_type == "play_song":
                        ui_state("thinking")
                        response = play_song(data)
                        ui_state("speaking")
                        ui_chat("Arfy", response)
                        speak(response)

                    elif command_type == "play_playlist":
                        ui_state("thinking")
                        response = play_playlist(data)
                        ui_state("speaking")
                        ui_chat("Arfy", response)
                        speak(response)

                    elif command_type == "pause_music":
                        response = pause_music()
                        ui_chat("Arfy", response)
                        speak(response)

                    elif command_type == "resume_music":
                        response = resume_music()
                        ui_chat("Arfy", response)
                        speak(response)

                    elif command_type == "next_song":
                        response = next_song()
                        ui_chat("Arfy", response)
                        speak(response)

                    elif command_type == "previous_song":
                        response = previous_song()
                        ui_chat("Arfy", response)
                        speak(response)

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
                    speak("Sorry, I had trouble processing that.")

# app entry point
app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

window = ArfyWindow()
window.show()
tray = ArfyTray(window)

arfy_thread = threading.Thread(target=arfy_loop, daemon=True)
arfy_thread.start()

sys.exit(app.exec())
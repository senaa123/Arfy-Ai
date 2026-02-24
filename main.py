import sys
import threading

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

print("Starting...")

try:
    from speech import speak, listen_with_type_fallback, wait_for_wake_word
    print("DONE: speech")

    from dotenv import load_dotenv
    load_dotenv()
    print("DONE: dotenv")

    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
    print("DONE: PyQt6")

    from Ui.main_window import ArfyWindow
    from Ui.tray import ArfyTray
    print("DONE: UI modules")

    # Grouping other imports
    from apps import open_app, close_app, parse_command
    from brain import ask_brain
    from spotify import play_song, pause_music, next_song, play_playlist, previous_song, resume_music
    print("DONE: Logic modules")

    print("DONE: All imports successful!")


except Exception as e:
    import traceback
    print(f"FAILED: {e}")
    traceback.print_exc()
    input("Press Enter to exit...")
    sys.exit(1)



# --- Thread-safe helpers ---
# These safely update the UI from a background thread
def ui_state(state):
    QMetaObject.invokeMethod(window, "set_state", Qt.ConnectionType.QueuedConnection,
                             Q_ARG(str, state))

def ui_chat(sender, message):
    QMetaObject.invokeMethod(window, "add_chat", Qt.ConnectionType.QueuedConnection,
                             Q_ARG(str, sender), Q_ARG(str, message))

def ui_song(name):
    QMetaObject.invokeMethod(window, "update_song", Qt.ConnectionType.QueuedConnection,
                             Q_ARG(str, name))


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

                # --- Exit Commands ---
                if any(word in text for word in ["goodbye", "sleep"]):
                    ui_state("speaking")
                    ui_chat("Arfy", "Goodbye Senaa!")
                    speak("Goodbye Senaa!")
                    active_chat = False
                    ui_state("idle")
                    break

                if any(word in text for word in ["stop", "exit", "quit"]):
                    speak("Shutting down! Bye Senaa!")
                    app.quit()
                    return  # Stop the thread too

                try:
                    command_type, data = parse_command(text)

                    if command_type == "open_app":
                        ui_state("speaking")
                        response = "Which app do you want to open?" if not data else \
                                   f"Opening {data}" if open_app(data) else f"Failed to open {data}"
                        ui_chat("Arfy", response)
                        speak(response)

                    elif command_type == "close_app":
                        while True:
                            ui_state("speaking")
                            speak(f"Are you sure you want to close {data}?")
                            ui_state("listening")
                            confirm = listen_with_type_fallback(8)

                            if confirm and any(w in confirm for w in ["yes", "yeah", "yep"]):
                                ui_state("speaking")
                                response = f"Closing {data}" if close_app(data) else f"Failed to close {data}"
                                ui_chat("Arfy", response)
                                speak(response)
                                break
                            elif confirm and any(w in confirm for w in ["no", "nah", "nope"]):
                                speak("Okay, not closing.")
                                break
                            else:
                                speak("Please say yes or no.")

                    elif command_type == "play_song":
                        ui_state("thinking")
                        response = play_song(data)
                        ui_song(data)
                        ui_state("speaking")
                        ui_chat("Arfy", response)
                        speak(response)

                    elif command_type == "play_playlist":
                        ui_state("thinking")
                        response = play_playlist(data)
                        ui_song(data + " playlist")
                        ui_state("speaking")
                        ui_chat("Arfy", response)
                        speak(response)

                    elif command_type == "pause_music":
                        pause_music()
                        speak("Music paused.")

                    elif command_type == "resume_music":
                        resume_music()
                        speak("Resuming music.")

                    elif command_type == "next_song":
                        next_song()
                        speak("Skipping to next song.")

                    elif command_type == "previous_song":
                        previous_song()
                        speak("Going back.")

                    else:  # ask_brain
                        ui_state("thinking")
                        response = ask_brain(data)
                        ui_state("speaking")
                        print(f"Arfy: {response}")
                        ui_chat("Arfy", response)
                        speak(response)
                        ui_state("listening")

                except Exception as e:
                    print(f"Error: {e}")
                    speak("Sorry, I had trouble with that.")


# --- App Entry Point ---
app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

window = ArfyWindow()
window.show()
tray = ArfyTray(window)

arfy_thread = threading.Thread(target=arfy_loop, daemon=True)
arfy_thread.start()

sys.exit(app.exec())
from dotenv import load_dotenv
load_dotenv()

from speech import speak, listen, listen_with_type_fallback, wait_for_wake_word
from apps import open_app, close_app, parse_command
from brain import ask_brain
from spotify import play_song, pause_music, next_song, play_playlist, previous_song, resume_music

if __name__ == "__main__":
    print("🤖 Arfy AI started!")
    speak("Hello! I am Arfy, your personal assistant!")

    while True:
        if wait_for_wake_word():
            speak("Yes Senaa!")
            active_chat = True

            while active_chat:
                text = listen_with_type_fallback()

                if text:
                    if any(word in text for word in ["goodbye", "sleep", "seeyou"]):
                        speak("Goodbye Senaa!")
                        active_chat = False
                        break

                    if any(word in text for word in ["stop", "exit", "quit"]):
                        speak("Shutting down! Bye Senaa!")
                        exit()

                    try:
                        command_type, data = parse_command(text)

                        if command_type == "open_app":
                            if not data:
                                speak("Which app do you want to open?")
                            elif open_app(data):
                                speak(f"Opening {data}")
                            else:
                                speak(f"Failed to open {data}")

                        elif command_type == "close_app":
                            while True:
                                speak(f"Are you sure you want to close {data}?")
                                text1 = listen(time_limit=8)
                                print(f"You said: {text1}")

                                if text1 and any(word in text1 for word in ["yes", "yeah", "yep", "correct"]):
                                    if close_app(data):
                                        speak(f"Closing {data}")
                                    else:
                                        speak(f"Failed to close {data}")
                                    break
                                elif text1 and any(word in text1 for word in ["no", "nah", "nope"]):
                                    speak("Okay, not closing the app.")
                                    break
                                else:
                                    speak("I didn't catch that. Please say yes or no.")
                                    continue

                        elif command_type == "play_song":
                            response = play_song(data)
                            speak(response)

                        elif command_type == "pause_music":
                            response = pause_music()
                            speak(response)

                        elif command_type == "resume_music":
                            response = resume_music()
                            speak(response)

                        elif command_type == "next_song":
                            response = next_song()
                            speak(response)

                        elif command_type == "previous_song":
                            response = previous_song()
                            speak(response)

                        elif command_type == "play_playlist":
                            response = play_playlist(data)
                            speak(response)

                        else:
                            response = ask_brain(data)
                            print(f"Arfy: {response}")
                            speak(response)

                    except Exception as e:
                        print(f"Error: {e}")
                        speak("Sorry, I had trouble processing that.")
                else:
                    continue
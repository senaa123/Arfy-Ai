import os
import speech_recognition as sr
from faster_whisper import WhisperModel
import edge_tts
import asyncio
import pygame
from memory import apply_corrections, load_memory
from voice_auth import is_owner_voice

pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

r = sr.Recognizer()
r.energy_threshold = 300
r.dynamic_energy_threshold = True

whisper_model = WhisperModel("medium", device="cuda", compute_type="float16")
whisper_wake = WhisperModel("tiny", device="cuda", compute_type="float16")

SPEECH_OUTPUT = "E:/Data Science/Arfy-Ai/Audio/speech_output.mp3"
TEMP_LISTEN = "E:/Data Science/Arfy-Ai/Audio/temp_listen.wav"
TEMP_WAKE = "E:/Data Science/Arfy-Ai/Audio/temp_wake.wav"

async def speak_async(text):
    communicate = edge_tts.Communicate(text, voice="en-IE-EmilyNeural")
    await communicate.save(SPEECH_OUTPUT)

def speak(text):
    asyncio.run(speak_async(text))
    pygame.mixer.music.load(SPEECH_OUTPUT)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        continue
    pygame.mixer.music.unload()

def get_prompt():
    memory = load_memory()
    known_words = [str(value) for value in memory.values() if isinstance(value, str)]
    base = "Senaa, Malabe, Eheliyagoda, Arfy, spotify, field"
    return base + ", " + ", ".join(known_words)

def listen(time_limit=5):
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=0.2)
        print("Listening...")
        try:
            audio = r.listen(source, timeout=time_limit, phrase_time_limit=10)
            print("Processing...")

            with open(TEMP_LISTEN, "wb") as f:
                f.write(audio.get_wav_data())

            segments, _ = whisper_model.transcribe(
                TEMP_LISTEN,
                language="en",
                initial_prompt=get_prompt()
            )

            text = " ".join([s.text for s in segments])
            text = apply_corrections(text)
            print(f"You said: {text}")
            return text.lower().strip()

        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            print("Could not understand audio")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None

def listen_with_type_fallback(time_limit=5):
    text = listen(time_limit)
    if text and any(phrase in text for phrase in ["let me type", "input field", "give me input", "i'll type", "let me write"]):
        speak("Sure, please type your input.")
        typed = input("Your input: ")
        return typed.lower().strip()
    return text

def wait_for_wake_word():
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=1)
        print("Standby Mode (Say 'Arfy')...")
        while True:
            try:
                audio = r.listen(source, timeout=2, phrase_time_limit=3)

                with open(TEMP_WAKE, "wb") as f:
                    f.write(audio.get_wav_data())

                if not is_owner_voice(TEMP_WAKE):
                    print("Unauthorized voice detected, ignoring...")
                    continue

                segments, _ = whisper_wake.transcribe(
                    TEMP_WAKE,
                    language="en",
                    initial_prompt="Arfy, stop, exit, quit, hey, hello"
                )

                text = " ".join([s.text for s in segments]).lower()
                print(f"Heard: {text}")

                if any(name in text for name in ["stop", "exit", "quit"]):
                    speak("Shutting down...")
                    exit()
                if any(name in text for name in ["arfy", "arfie", "alfie", "hey"]):
                    print("Wake word detected!")
                    return True

            except sr.WaitTimeoutError:
                continue
            except Exception as e:
                print(f"Error: {e}")
                continue
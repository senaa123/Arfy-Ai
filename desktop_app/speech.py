import os
from pathlib import Path
from typing import Optional

import speech_recognition as sr
from faster_whisper import WhisperModel

from memory import apply_corrections, load_memory

TEMP_LISTEN = Path("Audio/temp_listen.wav")

# SpeechRecognition setup
recognizer = sr.Recognizer()
recognizer.energy_threshold = 300
recognizer.dynamic_energy_threshold = True

# Keep Whisper model exactly as requested
whisper_model = WhisperModel("medium", device="cuda", compute_type="float16")


def get_prompt() -> str:
    """
    Build the initial prompt for Whisper using known memory values.
    """
    try:
        memory = load_memory()
        known_words = [str(value) for value in memory.values() if isinstance(value, str)]
    except Exception:
        known_words = []

    base = "Senaa, Malabe, Eheliyagoda, Arfy, spotify, field"

    if known_words:
        return base + ", " + ", ".join(known_words)
    return base


def _transcribe_file(audio_path: Path) -> Optional[str]:
    """
    Transcribe an audio file using Faster Whisper.
    """
    try:
        segments, _ = whisper_model.transcribe(
            str(audio_path),
            language="en",
            initial_prompt=get_prompt()
        )

        text = " ".join(segment.text for segment in segments).strip()
        if not text:
            return None

        text = apply_corrections(text)
        return text.lower().strip()

    except Exception as e:
        print(f"Transcription error: {e}")
        return None


def listen(time_limit: int = 5, phrase_time_limit: int = 10) -> Optional[str]:
    """
    Capture microphone audio and transcribe it.
    """
    with sr.Microphone() as source:
        try:
            recognizer.adjust_for_ambient_noise(source, duration=0.2)
            print("Listening...")

            audio = recognizer.listen(
                source,
                timeout=time_limit,
                phrase_time_limit=phrase_time_limit
            )

            print("Processing...")

            TEMP_LISTEN.parent.mkdir(parents=True, exist_ok=True)
            with open(TEMP_LISTEN, "wb") as file:
                file.write(audio.get_wav_data())

            text = _transcribe_file(TEMP_LISTEN)

            if text:
                print(f"You said: {text}")
            return text

        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            print("Could not understand audio")
            return None
        except Exception as e:
            print(f"Listen error: {e}")
            return None


def listen_with_type_fallback(time_limit: int = 5) -> Optional[str]:
    """
    Placeholder for future typed fallback.
    Currently just uses voice listen.
    """
    return listen(time_limit=time_limit)
from pathlib import Path
from typing import Optional

import speech_recognition as sr
from faster_whisper import WhisperModel

TEMP_LISTEN = Path("Audio/temp_listen.wav")

recognizer = sr.Recognizer()
recognizer.energy_threshold = 300
recognizer.dynamic_energy_threshold = True

_whisper_model = None


def get_whisper_model():
    """
    Load Whisper lazily so desktop startup stays lighter.
    """
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = WhisperModel("medium", device="cuda", compute_type="float16")
    return _whisper_model


def apply_corrections(text: str) -> str:
    """
    Local speech text correction hook.
    Keep this lightweight.
    """
    corrections = {
        "arfi": "arfy",
        "sena": "senaa",
        "vs code": "vscode",
    }

    fixed = text
    for wrong, right in corrections.items():
        fixed = fixed.replace(wrong, right)
    return fixed


def get_prompt() -> str:
    """
    Prompt words for Whisper to better recognize your common names and apps.
    """
    words = [
        "Senaa",
        "Arfy",
        "Malabe",
        "Eheliyagoda",
        "spotify",
        "chrome",
        "vscode",
        "notepad",
        "calculator",
    ]
    return ", ".join(words)


def _transcribe_file(audio_path: Path) -> Optional[str]:
    """
    Transcribe recorded WAV file using Faster Whisper.
    """
    try:
        model = get_whisper_model()

        segments, _ = model.transcribe(
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
    Capture microphone audio and transcribe it locally.
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

        except Exception as e:
            print(f"Listen error: {e}")
            return None

        finally:
            if TEMP_LISTEN.exists():
                try:
                    TEMP_LISTEN.unlink()
                except Exception:
                    pass


def listen_with_type_fallback(time_limit: int = 5) -> Optional[str]:
    """
    Future typed fallback hook.
    For now, just use voice.
    """
    return listen(time_limit=time_limit)
import os
import struct
import wave
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

import pvporcupine
from pvrecorder import PvRecorder
from voice_auth import is_owner_voice


env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

ACCESS_KEY = os.getenv("PICOVOICE_KEY")

HEY_ARFY_PATH = "Audio/wakeword/hey-ar-fy_en_windows_v4_0_0.ppn"
SHUTDOWN_ARFY_PATH = "Audio/wakeword/shutdown-afy_en_windows_v4_0_0.ppn"
TEMP_WAKE = Path("Audio/temp_wake.wav")


def save_wav(
    filename: Path,
    pcm_data: bytes,
    sample_rate: int = 16000,
    channels: int = 1,
    sampwidth: int = 2
) -> None:
    """
    Save raw PCM audio bytes as a WAV file.
    """
    filename.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(filename), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)


def record_followup_audio(recorder: PvRecorder, seconds: int = 2) -> Path:
    """
    Record a short follow-up clip after wake word detection for voice verification.
    """
    frames = []
    total_frames = int((recorder.sample_rate * seconds) / recorder.frame_length)

    for _ in range(total_frames):
        pcm = recorder.read()
        frames.append(struct.pack("<" + "h" * len(pcm), *pcm))

    audio_bytes = b"".join(frames)
    save_wav(TEMP_WAKE, audio_bytes, sample_rate=recorder.sample_rate)
    return TEMP_WAKE


def wait_for_wake_word() -> Optional[str]:
    """
    Wait until either:
    - 'hey Arfy' is detected -> returns 'wake'
    - 'shutdown Arfy' is detected -> returns 'shutdown'

    Performs owner voice verification before accepting the wake/shutdown phrase.
    """
    if not ACCESS_KEY:
        raise ValueError("PICOVOICE_KEY is not set in environment variables.")

    porcupine = None
    recorder = None

    try:
        porcupine = pvporcupine.create(
            access_key=ACCESS_KEY,
            keyword_paths=[HEY_ARFY_PATH, SHUTDOWN_ARFY_PATH],
            sensitivities=[0.7, 0.7]
        )

        recorder = PvRecorder(
            device_index=-1,
            frame_length=porcupine.frame_length
        )
        recorder.start()

        print("Standby Mode...")
        print("Say 'hey Arfy' to wake or 'shutdown Arfy' to exit.")

        while True:
            pcm = recorder.read()
            keyword_index = porcupine.process(pcm)

            if keyword_index == -1:
                continue

            print(f"Keyword detected: {keyword_index}")

            verify_file = record_followup_audio(recorder, seconds=2)

            if not is_owner_voice(str(verify_file)):
                print("Unauthorized voice detected, ignoring...")
                continue

            if keyword_index == 0:
                print("Wake phrase accepted.")
                return "wake"

            if keyword_index == 1:
                print("Shutdown phrase accepted.")
                return "shutdown"

    except Exception as e:
        print(f"Wake word error: {e}")
        return None

    finally:
        if recorder is not None:
            recorder.delete()
        if porcupine is not None:
            porcupine.delete()
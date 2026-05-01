import os
import struct
import wave
from pathlib import Path
from typing import Optional

import numpy as np
from dotenv import load_dotenv
from pvrecorder import PvRecorder
from openwakeword.model import Model

from .voice_auth import is_owner_voice


env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# -------------------------------------------------------------------
# openWakeWord custom model paths
# Replace these filenames with your actual trained model filenames.
# Example:
#   Audio/wakeword/hey_arfy.onnx
#   Audio/wakeword/shutdown_arfy.onnx
# -------------------------------------------------------------------

HEY_ARFY_PATH = PROJECT_ROOT / "Audio" / "wakeword" / "hey_Ruby.onnx"
SHUTDOWN_ARFY_PATH = PROJECT_ROOT / "Audio" / "wakeword" / "good_bye.onnx"

TEMP_WAKE = PROJECT_ROOT / "Audio" / "temp_wake.wav"

# Detection thresholds
WAKE_THRESHOLD = 0.5
SHUTDOWN_THRESHOLD = 0.5

# Recorder settings
INPUT_DEVICE_INDEX = -1
FRAME_LENGTH = 1280  # a common streaming chunk size for 16k audio
VERIFY_SECONDS = 2
COOLDOWN_SECONDS = 1.5


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
    Record a short follow-up clip after wake word detection
    for voice verification.
    """
    frames = []
    total_frames = int((recorder.sample_rate * seconds) / recorder.frame_length)

    for _ in range(total_frames):
        pcm = recorder.read()
        frames.append(struct.pack("<" + "h" * len(pcm), *pcm))

    audio_bytes = b"".join(frames)
    save_wav(TEMP_WAKE, audio_bytes, sample_rate=recorder.sample_rate)
    return TEMP_WAKE


def _validate_model_paths() -> None:
    """
    Ensure both custom openWakeWord model files exist.
    """
    for model_path in [HEY_ARFY_PATH, SHUTDOWN_ARFY_PATH]:
        if not model_path.exists():
            raise FileNotFoundError(f"Wake word model not found: {model_path}")


def _model_name_from_path(path: Path) -> str:
    """
    Convert:
        Audio/wakeword/hey_arfy.onnx
    into:
        hey_arfy
    """
    return path.stem


def _create_openwakeword_model() -> Model:
    """
    Create one openWakeWord detector that listens for both
    the wake phrase and the shutdown phrase.
    """
    _validate_model_paths()

    return Model(
        wakeword_models=[
            str(HEY_ARFY_PATH),
            str(SHUTDOWN_ARFY_PATH),
        ]
    )


def _normalize_audio_frame(pcm: list[int]) -> np.ndarray:
    """
    Convert PvRecorder output into the int16 numpy format expected
    by openWakeWord.
    """
    return np.array(pcm, dtype=np.int16)


def wait_for_wake_word() -> Optional[str]:
    """
    Wait until either:
    - wake phrase is detected -> returns 'wake'
    - shutdown phrase is detected -> returns 'shutdown'

    Performs owner voice verification before accepting the phrase.

    Keeps the same external behavior as the old Picovoice version,
    so the rest of the app does not need to change.
    """
    model = None
    recorder = None
    last_detection_time = 0.0

    wake_model_name = _model_name_from_path(HEY_ARFY_PATH)
    shutdown_model_name = _model_name_from_path(SHUTDOWN_ARFY_PATH)

    try:
        model = _create_openwakeword_model()

        recorder = PvRecorder(
            device_index=INPUT_DEVICE_INDEX,
            frame_length=FRAME_LENGTH
        )
        recorder.start()

        print("Standby Mode...")
        print("Say your wake phrase to wake or your shutdown phrase to exit.")

        while True:
            pcm = recorder.read()
            audio_frame = _normalize_audio_frame(pcm)

            scores = model.predict(audio_frame)
            if not isinstance(scores, dict):
                continue

            wake_score = float(scores.get(wake_model_name, 0.0))
            shutdown_score = float(scores.get(shutdown_model_name, 0.0))

            # Debug:
            # print(f"Wake score: {wake_score:.3f} | Shutdown score: {shutdown_score:.3f}")

            now = __import__("time").time()
            in_cooldown = (now - last_detection_time) < COOLDOWN_SECONDS
            if in_cooldown:
                continue

            detected_label = None

            # Check shutdown first so it can take priority if needed
            if shutdown_score >= SHUTDOWN_THRESHOLD:
                detected_label = "shutdown"
                print(f"Shutdown keyword detected (score={shutdown_score:.3f})")

            elif wake_score >= WAKE_THRESHOLD:
                detected_label = "wake"
                print(f"Wake keyword detected (score={wake_score:.3f})")

            if detected_label is None:
                continue

            # Prevent rapid duplicate triggers
            last_detection_time = now

            verify_file = record_followup_audio(recorder, seconds=VERIFY_SECONDS)

            if not is_owner_voice(str(verify_file)):
                print("Unauthorized voice detected, ignoring...")
                continue

            if detected_label == "wake":
                print("Wake phrase accepted.")
                return "wake"

            if detected_label == "shutdown":
                print("Shutdown phrase accepted.")
                return "shutdown"

    except Exception as e:
        print(f"Wake word error: {e}")
        return None

    finally:
        if recorder is not None:
            recorder.delete()

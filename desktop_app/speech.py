from pathlib import Path
from typing import Optional
from collections import deque
import queue
import time

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

from vad import SileroVAD, PreRollBuffer
from desktop_app.endpointing import EndpointingConfig, EndpointingState
from audio_utils import concat_frames, normalize_audio


TEMP_LISTEN = Path("Audio/temp_listen.wav")

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


def clean_transcript(text: str) -> str:
    """
    Basic transcript cleanup.
    """
    if not text:
        return ""

    text = text.strip()
    lower = text.lower()

    junk_phrases = {
        "thank you",
        "thanks for watching",
        "you",
        "uh",
        "um",
        "hmm",
    }

    if lower in junk_phrases:
        return ""

    wakeword_variants = [
        "hey arfy",
        "hi arfy",
        "okay arfy",
        "ok arfy",
        "jarvis",
    ]

    for phrase in wakeword_variants:
        if lower.startswith(phrase):
            text = text[len(phrase):].strip(" ,.!?")
            break

    if len(text.strip()) < 2:
        return ""

    return text.strip()


def get_prompt() -> str:
    """
    Prompt words for Whisper to better recognize your common names and apps.
    """
    words = [
        "Senaa",
        "Arfy",
        "Jarvis",
        "Malabe",
        "Eheliyagoda",
        "spotify",
        "chrome",
        "vscode",
        "notepad",
        "calculator",
    ]
    return ", ".join(words)


class SpeechRecorder:
    """
    Records one utterance after wake word using:
    - sounddevice input stream
    - Silero VAD
    - endpointing state machine
    - rolling VAD context window
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_ms: int = 32,
        channels: int = 1,
        vad_threshold: float = 0.25,
        input_device: int | None = None,
    ):
        self.sample_rate = sample_rate
        self.frame_ms = frame_ms
        self.channels = channels
        self.frame_samples = int(sample_rate * frame_ms / 1000)
        self.input_device = input_device

        self.audio_queue: "queue.Queue[np.ndarray]" = queue.Queue()

        self.vad = SileroVAD(sample_rate=sample_rate, threshold=vad_threshold)

        self.endpoint_config = EndpointingConfig(
            frame_ms=frame_ms,
            start_trigger_frames=1,
            end_silence_ms=700,
            preroll_ms=300,
            min_utterance_ms=250,
            max_utterance_ms=12000,
        )

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"[SpeechRecorder] Audio status: {status}")

        mono = indata[:, 0].copy()
        self.audio_queue.put(mono)

    def record_utterance(self, timeout_sec: float = 8.0) -> Optional[np.ndarray]:
        endpoint = EndpointingState(self.endpoint_config)

        preroll_frame_count = max(1, self.endpoint_config.preroll_ms // self.frame_ms)
        preroll = PreRollBuffer(max_frames=preroll_frame_count)

        # Use a larger rolling chunk for Silero instead of a single tiny frame
        vad_window_frames = deque(maxlen=8)  # ~256 ms at 32 ms/frame

        utterance_frames: list[np.ndarray] = []
        start_time = time.time()

        print("Sounddevice default input:", sd.default.device)

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            blocksize=self.frame_samples,
            device=self.input_device,
            callback=self._audio_callback,
        ):
            print("Listening...")

            while True:
                if time.time() - start_time > timeout_sec and not endpoint.in_speech:
                    print("[SpeechRecorder] Timeout waiting for speech.")
                    return None

                try:
                    frame = self.audio_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                if frame.ndim > 1:
                    frame = frame[:, 0]

                preroll.append(frame)
                vad_window_frames.append(frame)

                peak = float(np.max(np.abs(frame)))
                if peak > 0.02:
                    print(f"[SpeechRecorder] Mic peak: {peak:.3f}")

                vad_chunk = np.concatenate(list(vad_window_frames)).astype(np.float32)
                is_speech = self.vad.is_speech(vad_chunk)
                print(f"[SpeechRecorder] VAD speech: {is_speech}")

                state = endpoint.update(is_speech)

                if state == "speech_started":
                    print("[SpeechRecorder] Speech started.")
                    utterance_frames.extend(preroll.get_all())
                    utterance_frames.append(frame)

                elif state == "recording":
                    utterance_frames.append(frame)

                elif state in ("speech_ended", "max_len_reached"):
                    print(f"[SpeechRecorder] Speech ended: {state}")
                    utterance_frames.append(frame)
                    break

        if len(utterance_frames) < endpoint.min_frames:
            print("[SpeechRecorder] Utterance too short.")
            return None

        audio = concat_frames(utterance_frames)
        audio = normalize_audio(audio)
        return audio


def _transcribe_array(audio: np.ndarray) -> Optional[str]:
    """
    Transcribe in-memory waveform using Faster Whisper.
    """
    try:
        model = get_whisper_model()

        segments, _ = model.transcribe(
            audio,
            language="en",
            initial_prompt=get_prompt(),
            vad_filter=False,
            beam_size=1,
        )

        text = " ".join(segment.text for segment in segments).strip()
        if not text:
            return None

        text = apply_corrections(text)
        text = clean_transcript(text)

        if not text:
            return None

        return text.lower().strip()

    except Exception as e:
        print(f"Transcription error: {e}")
        return None


def listen(time_limit: int = 6) -> Optional[str]:
    """
    Capture microphone audio using VAD-based endpointing, then transcribe it.
    """
    try:
        recorder = SpeechRecorder(
            sample_rate=16000,
            frame_ms=32,
            channels=1,
            vad_threshold=0.25,
            input_device=None,
        )

        audio = recorder.record_utterance(timeout_sec=max(time_limit, 6))
        print("Captured audio:", audio is not None)

        if audio is None:
            return None

        print("Processing...")
        text = _transcribe_array(audio)
        print("Transcript result:", text)

        if text:
            print(f"You said: {text}")

        return text

    except Exception as e:
        print(f"Listen error: {e}")
        return None
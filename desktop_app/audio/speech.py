from pathlib import Path
from typing import Optional
from collections import deque
import gc
import queue
import sys
import time
import os

from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path)

# Keep MKL/OpenMP scratch allocations modest before numeric libraries load.
for _thread_env_name in (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ.setdefault(_thread_env_name, "1")
os.environ.setdefault("MKL_DISABLE_FAST_MM", "1")
os.environ.setdefault("KMP_BLOCKTIME", "0")

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

from .vad import SileroVAD, PreRollBuffer
from .endpointing import EndpointingConfig, EndpointingState
from .audio_utils import concat_frames, finalize_audio_for_asr
from .transcript_postprocess import postprocess_transcript

TEMP_LISTEN = Path("Audio/temp_listen.wav")

# Lazy-loaded whisper model cache
_whisper_model = None
_whisper_model_config: tuple[str, str, str] | None = None

# Stores the most recent finalized chunk captured for ASR
_last_captured_audio: Optional[np.ndarray] = None


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def _configured_whisper_model_name() -> str:
    return os.getenv("ARFY_WHISPER_MODEL", "base.en").strip() or "base.en"


def _configured_asr_device() -> str:
    return os.getenv("ARFY_ASR_DEVICE", "cpu").strip() or "cpu"


def _configured_asr_compute_type() -> str:
    return os.getenv("ARFY_ASR_COMPUTE_TYPE", "int8").strip() or "int8"


def _create_whisper_model(model_name: str, device: str, compute_type: str):
    print(f"Loading Whisper model: {model_name} on {device}/{compute_type}")
    return WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
        cpu_threads=_env_int("ARFY_ASR_CPU_THREADS", 1),
        num_workers=_env_int("ARFY_ASR_NUM_WORKERS", 1),
    )


def _release_whisper_model() -> None:
    global _whisper_model, _whisper_model_config

    old_model = _whisper_model
    _whisper_model = None
    _whisper_model_config = None
    del old_model
    gc.collect()

    torch = sys.modules.get("torch")
    cuda = getattr(torch, "cuda", None) if torch is not None else None
    if cuda is not None:
        try:
            if cuda.is_available():
                cuda.empty_cache()
        except Exception:
            pass


def _split_model_list(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _default_fallback_models(primary_model: str) -> list[str]:
    lower_name = primary_model.lower()
    if "large" in lower_name or "medium" in lower_name:
        return ["small.en", "base.en", "tiny.en"]
    if "small" in lower_name:
        return ["base.en", "tiny.en"]
    if "base" in lower_name:
        return ["tiny.en"]
    if "tiny" in lower_name:
        return []
    return ["tiny.en"]


def _fallback_model_names(primary_model: str) -> list[str]:
    configured = os.getenv("ARFY_ASR_FALLBACK_MODELS")
    fallback_models = (
        _split_model_list(configured)
        if configured is not None
        else _default_fallback_models(primary_model)
    )

    model_names: list[str] = []
    for model_name in [primary_model] + fallback_models:
        if model_name and model_name not in model_names:
            model_names.append(model_name)
    return model_names


def get_last_captured_audio() -> Optional[np.ndarray]:
    """
    Return the most recent finalized audio chunk captured for ASR.

    Useful for:
    - debugging
    - saving last recorded utterance
    - future speaker verification or analysis
    """
    return _last_captured_audio


def get_whisper_model():
    """
    Load Whisper lazily.

    Why:
    - Avoid loading the heavy model at desktop startup
    - Only load when user actually speaks
    """
    global _whisper_model, _whisper_model_config

    if _whisper_model is None:
        model_name = _configured_whisper_model_name()
        device = _configured_asr_device()
        compute_type = _configured_asr_compute_type()
        _whisper_model = _create_whisper_model(model_name, device, compute_type)
        _whisper_model_config = (model_name, device, compute_type)

    return _whisper_model


def _reset_whisper_model(
    *,
    model_name: str | None = None,
    device: str = "cpu",
    compute_type: str = "int8",
):
    """
    Recreate Whisper on a safer backend after GPU/cuDNN failures.
    """
    global _whisper_model, _whisper_model_config

    _release_whisper_model()
    model_name = model_name or _configured_whisper_model_name()
    _whisper_model = _create_whisper_model(model_name, device, compute_type)
    _whisper_model_config = (model_name, device, compute_type)
    return _whisper_model


def _resolve_input_device(sample_rate: int, channels: int) -> int | None:
    """
    Pick a stable input device.

    Windows MME defaults can fail with PaError -9999. Prefer an explicit
    ARFY_INPUT_DEVICE, then a WASAPI input, then PortAudio's default.
    """
    configured = os.getenv("ARFY_INPUT_DEVICE")
    if configured:
        try:
            return int(configured)
        except ValueError:
            pass

    try:
        devices = sd.query_devices()
    except Exception:
        return None

    wasapi_devices: list[int] = []
    directsound_devices: list[int] = []
    other_devices: list[int] = []
    for index, device_info in enumerate(devices):
        if int(device_info.get("max_input_channels", 0) or 0) < channels:
            continue

        hostapi_name = ""
        try:
            hostapi = sd.query_hostapis(device_info.get("hostapi"))
            hostapi_name = str(hostapi.get("name", ""))
        except Exception:
            pass

        upper_hostapi = hostapi_name.upper()
        if "WASAPI" in upper_hostapi:
            wasapi_devices.append(index)
        elif "DIRECTSOUND" in upper_hostapi:
            directsound_devices.append(index)
        else:
            other_devices.append(index)

    for index in wasapi_devices + directsound_devices + other_devices:
        try:
            sd.check_input_settings(
                device=index,
                samplerate=sample_rate,
                channels=channels,
                dtype="float32",
            )
            return index
        except Exception:
            continue

    return None


def get_prompt() -> str:
    """
    Prompt words given to Whisper so it better recognizes your common names/apps.

    This helps with:
    - Senaa
    - Arfy
    - common app names
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


def _transcribe_with_model(model, audio: np.ndarray) -> Optional[str]:
    segments, _ = model.transcribe(
        audio,
        language="en",
        initial_prompt=get_prompt(),
        vad_filter=False,
        beam_size=1,
    )

    text = " ".join(segment.text for segment in segments).strip()
    text = postprocess_transcript(text)
    return text.lower().strip() if text else None


class SpeechRecorder:
    """
    Records one utterance after wake word using:
    - sounddevice live input
    - Silero VAD
    - endpointing state machine
    - rolling VAD context window

    Flow:
    mic -> queue -> VAD -> endpointing -> collect frames -> finalize chunk
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

        # Number of samples per frame
        self.frame_samples = int(sample_rate * frame_ms / 1000)

        self.input_device = (
            input_device
            if input_device is not None
            else _resolve_input_device(sample_rate=sample_rate, channels=channels)
        )

        # Queue where callback thread places audio frames
        self.audio_queue: "queue.Queue[np.ndarray]" = queue.Queue()

        # Silero VAD for speech/non-speech detection
        self.vad = SileroVAD(sample_rate=sample_rate, threshold=vad_threshold)

        # Endpointing config controls actual start/end decisions
        self.endpoint_config = EndpointingConfig(
            frame_ms=frame_ms,
            start_trigger_frames=1,
            end_silence_ms=700,
            preroll_ms=300,
            min_utterance_ms=250,
            max_utterance_ms=12000,
        )

    def _audio_callback(self, indata, frames, time_info, status):
        """
        sounddevice callback.

        Called repeatedly by the audio stream.
        We copy the first channel and push it into a queue.
        """
        if status:
            print(f"[SpeechRecorder] Audio status: {status}")

        mono = indata[:, 0].copy()
        self.audio_queue.put(mono)

    def record_utterance(self, timeout_sec: float = 8.0) -> Optional[np.ndarray]:
        """
        Record one utterance using VAD + endpointing.

        Steps:
        1. wait for speech
        2. use pre-roll so start of speech is not cut
        3. keep recording until endpointing says stop
        4. concatenate frames
        5. trim silence and normalize before returning
        """
        endpoint = EndpointingState(self.endpoint_config)

        # Number of frames to keep before speech officially starts
        preroll_frame_count = max(1, self.endpoint_config.preroll_ms // self.frame_ms)
        preroll = PreRollBuffer(max_frames=preroll_frame_count)

        # Rolling window for VAD so detection is more stable than using one tiny frame
        vad_window_frames = deque(maxlen=8)  # ~256 ms total at 32 ms per frame

        utterance_frames: list[np.ndarray] = []
        start_time = time.time()

        print("Sounddevice default input:", sd.default.device)
        print("Sounddevice selected input:", self.input_device)

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
                # Timeout only while still waiting for speech to begin
                if time.time() - start_time > timeout_sec and not endpoint.in_speech:
                    print("[SpeechRecorder] Timeout waiting for speech.")
                    return None

                try:
                    frame = self.audio_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                # Safety: if frame unexpectedly has multiple dims, keep first channel
                if frame.ndim > 1:
                    frame = frame[:, 0]

                # Always keep frame in preroll buffer
                preroll.append(frame)

                # Also keep frame in the rolling VAD context window
                vad_window_frames.append(frame)

                # Simple mic level debug
                peak = float(np.max(np.abs(frame)))
                if peak > 0.02:
                    print(f"[SpeechRecorder] Mic peak: {peak:.3f}")

                # Concatenate recent frames and run VAD over a slightly larger chunk
                vad_chunk = np.concatenate(list(vad_window_frames)).astype(np.float32)
                is_speech = self.vad.is_speech(vad_chunk)
                print(f"[SpeechRecorder] VAD speech: {is_speech}")

                # Endpointing decides if speech started / continues / ended
                state = endpoint.update(is_speech)

                if state == "speech_started":
                    print("[SpeechRecorder] Speech started.")

                    # Add preroll so the first syllable is not cut off
                    utterance_frames.extend(preroll.get_all())
                    utterance_frames.append(frame)

                elif state == "recording":
                    utterance_frames.append(frame)

                elif state in ("speech_ended", "max_len_reached"):
                    print(f"[SpeechRecorder] Speech ended: {state}")
                    utterance_frames.append(frame)
                    break

        # Reject chunks that are too short to be meaningful
        if len(utterance_frames) < endpoint.min_frames:
            print("[SpeechRecorder] Utterance too short.")
            return None

        # Merge all frames into one waveform
        audio = concat_frames(utterance_frames)

        # Final cleanup before ASR
        audio = finalize_audio_for_asr(
            audio,
            sample_rate=self.sample_rate,
            normalize=True,
            trim=True,
            trim_threshold=0.01,
            trim_keep_ms=80,
        )

        if audio.size == 0:
            print("[SpeechRecorder] Finalized audio is empty after trimming.")
            return None

        return audio


def _transcribe_array(audio: np.ndarray) -> Optional[str]:
    """
    Transcribe an in-memory waveform using Faster Whisper.

    Steps:
    1. transcribe raw finalized audio
    2. clean transcript using transcript_postprocess.py
    3. reject low-content result if cleanup returns empty
    """
    audio = np.ascontiguousarray(audio, dtype=np.float32)

    try:
        model = get_whisper_model()
        return _transcribe_with_model(model, audio)

    except Exception as e:
        print(f"Transcription error: {e}")

        model_config = _whisper_model_config or ("", "", "")
        primary_model = model_config[0] or _configured_whisper_model_name()

        for fallback_model_name in _fallback_model_names(primary_model):
            fallback_config = (fallback_model_name, "cpu", "int8")
            if fallback_config == model_config:
                continue

            try:
                print(
                    "Retrying transcription with "
                    f"{fallback_model_name} on CPU/int8..."
                )
                model = _reset_whisper_model(
                    model_name=fallback_model_name,
                    device="cpu",
                    compute_type="int8",
                )
                return _transcribe_with_model(model, audio)
            except Exception as fallback_error:
                print(
                    "Transcription retry failed for "
                    f"{fallback_model_name} on CPU/int8: {fallback_error}"
                )

        return None


def listen(time_limit: int = 6) -> Optional[str]:
    """
    Capture microphone audio using VAD-based endpointing, then transcribe it.

    Full pipeline:
    mic -> VAD -> endpointing -> finalize audio -> Whisper -> transcript cleanup
    """
    global _last_captured_audio

    try:
        recorder = SpeechRecorder(
            sample_rate=16000,
            frame_ms=32,
            channels=1,
            vad_threshold=0.25,
            input_device=None,
        )

        # Record one utterance
        audio = recorder.record_utterance(timeout_sec=max(time_limit, 6))
        print("Captured audio:", audio is not None)

        if audio is None:
            _last_captured_audio = None
            return None

        # Save finalized audio for debugging / later use
        _last_captured_audio = audio

        print("Processing...")
        text = _transcribe_array(audio)
        print("Transcript result:", text)

        if text:
            print(f"You said: {text}")

        return text

    except Exception as e:
        print(f"Listen error: {e}")
        _last_captured_audio = None
        return None


def listen_with_type_fallback(time_limit: int = 6) -> Optional[str]:
    """
    Compatibility wrapper.

    Why:
    - Your older code still imports this function name
    - Keeps old callers working without changing them immediately
    """
    return listen(time_limit=time_limit)

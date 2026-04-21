import numpy as np


def pcm_bytes_to_float32(audio_bytes: bytes) -> np.ndarray:
    """
    Convert raw 16-bit PCM bytes into a float32 numpy array in range [-1, 1].

    Why:
    - Some tools return raw PCM bytes
    - Whisper / VAD processing is easier with float32 arrays
    """
    audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
    audio = audio / 32768.0
    return audio


def float32_to_pcm16_bytes(audio: np.ndarray) -> bytes:
    """
    Convert float32 waveform in [-1, 1] into 16-bit PCM bytes.

    Why:
    - Useful when another tool expects PCM16 audio
    """
    audio = np.clip(audio, -1.0, 1.0)
    audio_int16 = (audio * 32767).astype(np.int16)
    return audio_int16.tobytes()


def ensure_mono_float32(audio: np.ndarray) -> np.ndarray:
    """
    Return audio as a 1D mono float32 waveform.

    What this does:
    - If audio is stereo / multi-channel, keep only the first channel
    - Always return float32

    Why:
    - Keeps one standard internal format for ASR and post-processing
    """
    audio = np.asarray(audio)

    if audio.ndim == 2:
        audio = audio[:, 0]

    return audio.astype(np.float32, copy=False)


def normalize_audio(audio: np.ndarray, target_peak: float = 0.95) -> np.ndarray:
    """
    Normalize audio peak amplitude.

    Why:
    - Makes quiet and loud mic input more consistent
    - Helps ASR when input volume changes

    target_peak:
    - 0.95 means normalize near full scale without clipping
    """
    audio = ensure_mono_float32(audio)

    if audio.size == 0:
        return audio

    peak = np.max(np.abs(audio))

    # If signal is basically silence, do nothing
    if peak < 1e-6:
        return audio

    scale = target_peak / peak
    return np.clip(audio * scale, -1.0, 1.0)


def trim_silence(
    audio: np.ndarray,
    sample_rate: int,
    threshold: float = 0.01,
    keep_ms: int = 80,
) -> np.ndarray:
    """
    Trim leading and trailing near-silence while keeping a little padding.

    Parameters:
    - threshold: anything below this abs amplitude is treated as silence
    - keep_ms: keep a small margin so speech does not sound cut too tight

    Why:
    - Removes extra silence before and after the utterance
    - Speeds up transcription slightly
    - Makes chunk cleaner for ASR
    """
    audio = ensure_mono_float32(audio)

    if audio.size == 0:
        return audio

    # Find all positions where audio is above silence threshold
    active = np.flatnonzero(np.abs(audio) >= threshold)

    # If nothing is active, just return original
    if active.size == 0:
        return audio

    keep = ms_to_samples(keep_ms, sample_rate)

    # Trim start and end, but keep a little extra margin
    start = max(0, int(active[0]) - keep)
    end = min(audio.size, int(active[-1]) + keep + 1)

    return audio[start:end]


def finalize_audio_for_asr(
    audio: np.ndarray,
    sample_rate: int,
    normalize: bool = True,
    trim: bool = True,
    trim_threshold: float = 0.01,
    trim_keep_ms: int = 80,
) -> np.ndarray:
    """
    Final canonical cleanup step before ASR.

    Pipeline:
    1. force mono float32
    2. trim silence
    3. normalize volume

    Why:
    - Keeps ASR input consistent
    - Central place for final audio cleanup
    """
    audio = ensure_mono_float32(audio)

    if trim:
        audio = trim_silence(
            audio,
            sample_rate=sample_rate,
            threshold=trim_threshold,
            keep_ms=trim_keep_ms,
        )

    if normalize:
        audio = normalize_audio(audio)

    return audio


def concat_frames(frames: list[np.ndarray]) -> np.ndarray:
    """
    Concatenate a list of audio frames into one waveform.

    Why:
    - During live capture, audio comes frame by frame
    - Before ASR, we need one continuous waveform
    """
    if not frames:
        return np.array([], dtype=np.float32)

    return np.concatenate([ensure_mono_float32(frame) for frame in frames]).astype(np.float32)


def ms_to_samples(ms: int, sample_rate: int) -> int:
    """
    Convert milliseconds to number of audio samples.
    """
    return int((ms / 1000.0) * sample_rate)
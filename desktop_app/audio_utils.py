import numpy as np


def pcm_bytes_to_float32(audio_bytes: bytes) -> np.ndarray:
    """
    Convert raw 16-bit PCM bytes into float32 numpy array in [-1, 1].
    """
    audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
    audio = audio / 32768.0
    return audio


def float32_to_pcm16_bytes(audio: np.ndarray) -> bytes:
    """
    Convert float32 waveform in [-1, 1] into 16-bit PCM bytes.
    """
    audio = np.clip(audio, -1.0, 1.0)
    audio_int16 = (audio * 32767).astype(np.int16)
    return audio_int16.tobytes()


def normalize_audio(audio: np.ndarray, target_peak: float = 0.95) -> np.ndarray:
    """
    Normalize audio peak amplitude.
    """
    if audio.size == 0:
        return audio

    peak = np.max(np.abs(audio))

    # Return as-is only for silent / near-silent audio
    if peak < 1e-6:
        return audio

    scale = target_peak / peak
    return np.clip(audio * scale, -1.0, 1.0)


def concat_frames(frames: list[np.ndarray]) -> np.ndarray:
    """
    Concatenate a list of audio frames into a single waveform.
    """
    if not frames:
        return np.array([], dtype=np.float32)

    return np.concatenate(frames).astype(np.float32)


def ms_to_samples(ms: int, sample_rate: int) -> int:
    """
    Convert milliseconds to number of audio samples.
    """
    return int((ms / 1000.0) * sample_rate)
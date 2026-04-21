from collections import deque
import numpy as np
from silero_vad import load_silero_vad, get_speech_timestamps


class SileroVAD:
    """
    Wrapper around Silero VAD.

    Notes:
    - Input should be mono float32 audio in range [-1, 1]
    - Works better when called on a short rolling chunk, not a single tiny frame
    """

    def __init__(self, sample_rate: int = 16000, threshold: float = 0.25):
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.model = load_silero_vad()

    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        """
        Check whether the provided chunk contains speech.

        Args:
            audio_chunk: 1D mono float32 waveform.

        Returns:
            bool: True if speech detected, else False.
        """
        if audio_chunk.dtype != np.float32:
            audio_chunk = audio_chunk.astype(np.float32)

        speech_segments = get_speech_timestamps(
            audio_chunk,
            self.model,
            sampling_rate=self.sample_rate,
            threshold=self.threshold,
        )
        return len(speech_segments) > 0


class PreRollBuffer:
    """
    Small rolling buffer that stores the most recent frames.
    """

    def __init__(self, max_frames: int):
        self.buffer = deque(maxlen=max_frames)

    def append(self, frame: np.ndarray) -> None:
        self.buffer.append(frame.copy())

    def get_all(self) -> list[np.ndarray]:
        return list(self.buffer)

    def clear(self) -> None:
        self.buffer.clear()
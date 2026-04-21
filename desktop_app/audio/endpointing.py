from dataclasses import dataclass


@dataclass
class EndpointingConfig:
    """
    Configuration values for speech endpointing.
    """
    frame_ms: int = 32
    start_trigger_frames: int = 3
    end_silence_ms: int = 1200
    preroll_ms: int = 300
    min_utterance_ms: int = 300
    max_utterance_ms: int = 12000


class EndpointingState:
    """
    Runtime state machine for live endpointing.
    """

    def __init__(self, config: EndpointingConfig):
        self.config = config
        self.reset()

    def reset(self):
        self.in_speech = False
        self.speech_count = 0
        self.silence_count = 0
        self.total_frames = 0

    @property
    def silence_frames_needed(self) -> int:
        return max(1, self.config.end_silence_ms // self.config.frame_ms)

    @property
    def max_frames(self) -> int:
        return max(1, self.config.max_utterance_ms // self.config.frame_ms)

    @property
    def min_frames(self) -> int:
        return max(1, self.config.min_utterance_ms // self.config.frame_ms)

    def update(self, is_speech: bool) -> str:
        self.total_frames += 1

        if not self.in_speech:
            if is_speech:
                self.speech_count += 1
            else:
                self.speech_count = 0

            if self.speech_count >= self.config.start_trigger_frames:
                self.in_speech = True
                self.silence_count = 0
                return "speech_started"

            return "waiting"

        if is_speech:
            self.silence_count = 0
        else:
            self.silence_count += 1

        if self.silence_count >= self.silence_frames_needed:
            return "speech_ended"

        if self.total_frames >= self.max_frames:
            return "max_len_reached"

        return "recording"
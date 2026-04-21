import asyncio
from pathlib import Path

import edge_tts
import pygame

VOICE_NAME = "en-IE-EmilyNeural"
SPEECH_OUTPUT = Path("Audio/speech_output.mp3")

# Initialize pygame mixer once
if not pygame.mixer.get_init():
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)


async def speak_async(text: str, voice: str = VOICE_NAME) -> None:
    """
    Generate TTS audio and save it to a file.
    """
    communicate = edge_tts.Communicate(text, voice=voice)
    await communicate.save(str(SPEECH_OUTPUT))


def speak(text: str, voice: str = VOICE_NAME) -> None:
    """
    Blocking TTS playback.
    Generates speech, plays it, and waits until playback finishes.
    """
    if not text or not text.strip():
        return

    asyncio.run(speak_async(text, voice=voice))

    pygame.mixer.music.load(str(SPEECH_OUTPUT))
    pygame.mixer.music.play()

    clock = pygame.time.Clock()
    while pygame.mixer.music.get_busy():
        clock.tick(20)

    pygame.mixer.music.unload()
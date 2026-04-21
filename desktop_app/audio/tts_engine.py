import asyncio
from pathlib import Path
import os
import time

import pygame
import edge_tts

SPEECH_OUTPUT = Path("Audio/output.mp3")
DEFAULT_VOICE = "en-US-AriaNeural"


def clean_tts_text(text: str) -> str:
    """
    Clean text before sending to edge-tts.
    """
    if not text:
        return ""

    text = text.strip()

    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        text = text[1:-1].strip()

    text = " ".join(text.split())
    return text


def prepare_output_file():
    """
    Make sure the output file is not locked before writing.
    """
    SPEECH_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    if pygame.mixer.get_init():
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

        try:
            pygame.mixer.music.unload()
        except Exception:
            pass

    if SPEECH_OUTPUT.exists():
        for _ in range(5):
            try:
                os.remove(SPEECH_OUTPUT)
                break
            except PermissionError:
                time.sleep(0.1)


async def speak_async(text: str, voice: str = DEFAULT_VOICE):
    """
    Generate speech with edge-tts and play it with pygame.
    """
    text = clean_tts_text(text)
    if not text:
        return

    prepare_output_file()

    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(str(SPEECH_OUTPUT))

    if not pygame.mixer.get_init():
        pygame.mixer.init()

    pygame.mixer.music.load(str(SPEECH_OUTPUT))
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        await asyncio.sleep(0.1)

    try:
        pygame.mixer.music.unload()
    except Exception:
        pass


def speak(text: str, voice: str = DEFAULT_VOICE):
    """
    Safe sync wrapper so Arfy does not crash if TTS fails.
    """
    try:
        asyncio.run(speak_async(text, voice=voice))
    except Exception as e:
        print(f"TTS error: {e}")
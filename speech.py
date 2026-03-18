import os
import speech_recognition as sr
import struct, wave
import pvporcupine
from faster_whisper import WhisperModel
from pvrecorder import PvRecorder
import edge_tts
import asyncio
import pygame
from memory import apply_corrections, load_memory
from voice_auth import is_owner_voice

pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

r = sr.Recognizer()
r.energy_threshold = 300
r.dynamic_energy_threshold = True

whisper_model = WhisperModel("medium", device="cuda", compute_type="float16")
#whisper_wake = WhisperModel("tiny", device="cuda", compute_type="float16")

ACCESS_KEY = os.getenv("PICOVOICE_KEY")

HEY_ARFY_PATH = "Audio/wakeword/hey-ar-fy_en_windows_v4_0_0.ppn"
SHUTDOWN_ARFY_PATH = "Audio/wakeword/shutdown-afy_en_windows_v4_0_0.ppn"
SPEECH_OUTPUT = "E:/Data Science/Arfy-Ai/Audio/speech_output.mp3"
TEMP_LISTEN = "E:/Data Science/Arfy-Ai/Audio/temp_listen.wav"
TEMP_WAKE = "Audio/temp_wake.wav"

async def speak_async(text):
    communicate = edge_tts.Communicate(text, voice="en-IE-EmilyNeural")
    await communicate.save(SPEECH_OUTPUT)

def speak(text):
    asyncio.run(speak_async(text))
    pygame.mixer.music.load(SPEECH_OUTPUT)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        continue
    pygame.mixer.music.unload()

def get_prompt():
    memory = load_memory()
    known_words = [str(value) for value in memory.values() if isinstance(value, str)]
    base = "Senaa, Malabe, Eheliyagoda, Arfy, spotify, field"
    return base + ", " + ", ".join(known_words)

def listen(time_limit=5):
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=0.2)
        print("Listening...")
        try:
            audio = r.listen(source, timeout=time_limit, phrase_time_limit=10)
            print("Processing...")

            with open(TEMP_LISTEN, "wb") as f:
                f.write(audio.get_wav_data())

            segments, _ = whisper_model.transcribe(
                TEMP_LISTEN,
                language="en",
                initial_prompt=get_prompt()
            )

            text = " ".join([s.text for s in segments])
            text = apply_corrections(text)
            print(f"You said: {text}")
            return text.lower().strip()

        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            print("Could not understand audio")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None

def listen_with_type_fallback(time_limit=5):
    text = listen(time_limit)
    
    return text

def save_wav(filename, pcm_data, sample_rate=16000, channels=1, sampwidth=2):
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)

def record_followup_audio(recorder, seconds=2):
    frames = []
    total_frames = int((recorder.sample_rate * seconds) / recorder.frame_length)

    for _ in range(total_frames):
        pcm = recorder.read()
        frames.append(struct.pack("<" + "h" * len(pcm), *pcm))

    audio_bytes = b"".join(frames)
    save_wav(TEMP_WAKE, audio_bytes, sample_rate=recorder.sample_rate)
    return TEMP_WAKE

def wait_for_wake_word():
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

            if not is_owner_voice(verify_file):
                print("Unauthorized voice detected, ignoring...")
                continue

            if keyword_index == 0:
                print("Wake phrase accepted.")
                return "wake"

            elif keyword_index == 1:
                print("Shutdown phrase accepted.")
                return "shutdown"

    finally:
        if recorder is not None:
            recorder.delete()
        if porcupine is not None:
            porcupine.delete()
    
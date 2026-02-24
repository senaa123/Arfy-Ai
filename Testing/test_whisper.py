import speech_recognition as sr

r = sr.Recognizer()
print("Whisper STT Test - Speak clearly after 'Listening...'")

with sr.Microphone() as source:
    r.adjust_for_ambient_noise(source, duration=1)
    print("Listening...")
    audio = r.listen(source, timeout=10, phrase_time_limit=5)

print("Processing speech...")
try:
    text = r.recognize_whisper(audio, model="base")
    print(f"✅ You said: '{text}'")
except sr.UnknownValueError:
    print("❌ Could not understand audio")
except sr.RequestError as e:
    print(f"❌ Error: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")

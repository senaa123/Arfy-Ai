import speech_recognition as sr

r = sr.Recognizer()
print("Testing microphone... Say something!")

with sr.Microphone() as source:
    print("Listening...")
    audio = r.listen(source, timeout=5)
    print("Got it! Processing...")

try:
    text = r.recognize_whisper(audio, model='base')
    print(f"You said: {text}")
except Exception as e:
    print(f"Error: {e}")

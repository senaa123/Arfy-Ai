import speech_recognition as sr

r = sr.Recognizer()
print('Microphone test...')

try:
    m = sr.Microphone()
    print(f'✅ Microphone found: {m.device_index}')
    print('SpeechRecognition library is working!')
except Exception as e:
    print(f'❌ Error: {e}')

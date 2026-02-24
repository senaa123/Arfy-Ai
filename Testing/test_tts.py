import pyttsx3

print("Testing Text-to-Speech (TTS)...")

try:
    engine = pyttsx3.init()
    
    # Get available voices
    voices = engine.getProperty('voices')
    print(f"✅ TTS engine initialized: {len(voices)} voices available")
    
    # Test speech
    print("Speaking: 'Hello Senan, I am Arfy, your AI brain. Can you hear me?'")
    engine.say("Hello Senan, I am Arfy, your AI brain. Can you hear me?")
    engine.runAndWait()
    
    print("✅ TTS test completed successfully!")
    
except Exception as e:
    print(f"❌ TTS Error: {e}")
    print("\nTroubleshooting:")
    print("1. Install/reinstall: pip install pyttsx3")
    print("2. On Windows, ensure SAPI5 is available")

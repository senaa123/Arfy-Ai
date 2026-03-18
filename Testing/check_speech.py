import sys
import traceback
import os

# Set UTF-8 encoding for Windows terminals
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

print("Starting Speech Test...")
try:
    from speech import whisper_model
    print(f"Whisper Model Status: {whisper_model}")
    print("SUCCESS: Speech module loaded!")
except Exception as e:
    print(f"FAILED: {e}")
    traceback.print_exc()

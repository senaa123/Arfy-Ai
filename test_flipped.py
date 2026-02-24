import sys
import traceback

# Set UTF-8 encoding for Windows terminals
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

print("Starting Flipped Order Test...")

try:
    print("Step 1: Importing speech first...")
    from speech import whisper_model
    print(f"DONE: speech (Status: {whisper_model})")

    print("Step 2: Importing PyQt6...")
    from PyQt6.QtWidgets import QApplication
    print("DONE: PyQt6")

    print("SUCCESS: Flipped order test passed!")
except Exception as e:
    print(f"FAILED: {e}")
    traceback.print_exc()

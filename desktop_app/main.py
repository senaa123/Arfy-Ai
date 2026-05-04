import sys
import threading
from pathlib import Path

from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication

from .runtime import ArfyDesktopRuntime
from .ui.main_window import ArfyWindow
from .ui.tray import ArfyTray
from .ui_bridge import DesktopUIBridge

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)


app = QApplication(sys.argv) # create the PyQt app
app.setQuitOnLastWindowClosed(False) # keep running even if the window closed

window = ArfyWindow()
window.show()

# create components
tray = ArfyTray(window)
ui = DesktopUIBridge(window)
runtime = ArfyDesktopRuntime(app=app, window=window, ui=ui)

# Route typed UI input into the runtime queue.
window.text_submitted.connect(runtime.submit_text)

# Keep the assistant loop off the UI thread.
arfy_thread = threading.Thread(target=runtime.arfy_loop, daemon=True)
arfy_thread.start()

sys.exit(app.exec())

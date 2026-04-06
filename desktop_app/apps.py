import os
import subprocess

APP_COMMANDS = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "spotify": r"C:\Users\ASUS\AppData\Roaming\Spotify\Spotify.exe",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "vscode": r"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "explorer": "explorer.exe",
}


def open_app(app_name: str) -> bool:
    """
    Open a known allowed desktop app.
    """
    app_name = app_name.strip().lower()

    if app_name not in APP_COMMANDS:
        return False

    try:
        command = os.path.expandvars(APP_COMMANDS[app_name])
        subprocess.Popen(command)
        return True
    except Exception as e:
        print(f"open_app error: {e}")
        return False


def close_app(app_name: str) -> bool:
    """
    Close a known allowed desktop app by process image name.
    """
    app_name = app_name.strip().lower()

    process_map = {
        "chrome": "chrome.exe",
        "notepad": "notepad.exe",
        "calculator": "CalculatorApp.exe",
        "vscode": "Code.exe",
        "explorer": "explorer.exe",
        "spotify": "Spotify.exe",
    }

    if app_name not in process_map:
        return False

    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", process_map[app_name]],
            check=False,
            capture_output=True,
            text=True
        )
        return True
    except Exception as e:
        print(f"close_app error: {e}")
        return False
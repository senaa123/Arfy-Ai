# apps.py
import string
import subprocess

APP = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "notepad": "notepad.exe",
    "calculator": "CalculatorApp",
    "spotify": r"C:\Users\ASUS\AppData\Roaming\Spotify\Spotify.exe",
    "file explorer": "explorer.exe",
    "vscode": r"C:\Users\ASUS\AppData\Local\Programs\Microsoft VS Code\code.exe",
}

def open_app(app_name):
    if not app_name:
        return False
    if app_name in APP:
        path = APP[app_name]
        subprocess.Popen(f'"{path}"', shell=True)
        return True
    try:
        subprocess.Popen(f'start "" "{app_name}"', shell=True)
        return True
    except:
        return False

def close_app(app_name):
    if not app_name:
        return False
    target = app_name
    if app_name in APP:
        target = APP[app_name].split("\\")[-1].replace(".exe", "")
    result = subprocess.run(f"taskkill /F /IM {target}.exe", shell=True)
    return result.returncode == 0

def parse_command(text):
    
    text = text.lower()
    if "open" in text:
        app = text.split("open")[-1].strip()
        return ("open_app", app)
    
    elif "close" in text:
        app = text.split("close")[-1].strip(string.punctuation)
        return ("close_app", app)
    
    elif "play" in text:

        if "playlist" in text:
            name = text.split("playlist")[-1].strip()
            return ("play_playlist", name)
        else:
            song =  text.split("play")[-1].strip()
            return ("play_song", song)
        
    elif text and any(word in text for word in ["pause", "stop music","hold music"]):
        return ("pause_music", "")
    
    elif text and any(word in text for word in ["resume", "continue music","unpause"]):
        return ("resume_music", "")
    
    elif "next song" in text or "skip" in text:
        return ("next_song", "")
    
    elif "previous" in text or "go back" in text or "last song" in text:
        return ("previous_song", "")
    
    else:
        return ("ask_brain", text)
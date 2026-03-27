# apps.py
import string
import subprocess

DETACHED = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

APP = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "spotify": r"C:\Users\ASUS\AppData\Roaming\Spotify\Spotify.exe",
    "file explorer": "explorer.exe",
    "vscode": r"C:\Users\ASUS\AppData\Local\Programs\Microsoft VS Code\code.exe",
}

def open_app(app_name):
    if not app_name:
        return False
    
    app_name = app_name.lower().strip()
    try:
        if app_name in APP:
            path = APP[app_name]
            subprocess.Popen(
                path,
                shell=False,
                creationflags=DETACHED,  # detaches sthe tools from the process
                close_fds=True,# don't copy file descriptors
                stdin=subprocess.DEVNULL,# no stdin handle inherited  
                stdout=subprocess.DEVNULL, # no stdout handle inherited
                stderr=subprocess.DEVNULL # no stderr handle inherited
                )
        else:
            subprocess.Popen(
                f'start "" "{app_name}"',#try from the shell start
                    shell=True,
                    creationflags=DETACHED,
                    close_fds=True,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
            )
            return True
    except Exception as e:
        print(f"Open app error: {e}")
        return False

def close_app(app_name):
    if not app_name:
        return False
    target = app_name
    if app_name in APP:
        target = APP[app_name].split("\\")[-1].replace(".exe", "")
    result = subprocess.run(
        f"taskkill /F /IM {target}.exe",
        shell=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return result.returncode == 0

def parse_command(text):
    
    text = text.lower()
    if "open" in text:
        words = text.split()
        
        for word in words:
            clean_word = word.strip(string.punctuation)
            if clean_word in APP:
                return ("open_app", clean_word)
    
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
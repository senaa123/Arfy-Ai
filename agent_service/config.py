import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

# Main model used for general reasoning / responses
GROQ_MODEL_MAIN = os.getenv("GROQ_MODEL_MAIN")

# Smaller/faster model for intent routing if you want one
GROQ_MODEL_ROUTER = os.getenv("GROQ_MODEL_ROUTER")

# Groq API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Memory service base URL
MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL")

# Safety config
MAX_SESSION_TURNS = int(os.getenv("MAX_SESSION_TURNS", "12"))
REPEAT_BLOCK_WINDOW_SECONDS = int(os.getenv("REPEAT_BLOCK_WINDOW_SECONDS", "60"))
REPEAT_BLOCK_COUNT = int(os.getenv("REPEAT_BLOCK_COUNT", "3"))

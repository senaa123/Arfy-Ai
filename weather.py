import requests
import os
from memory import load_memory
from dotenv import load_dotenv
load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
WEATHER_URL = "http://api.openweathermap.org/data/2.5/weather"

def get_weather(location):
    if not WEATHER_API_KEY:
        print("Error: WEATHER_API_KEY is not found.")
        return None
    try:
        response = requests.get(WEATHER_URL, params={
            "q": location,
            "appid": WEATHER_API_KEY,
            "units": "metric"
        })
        data = response.json()
        #print(f"API response: {data}")  # debugging

        if data.get("cod") == 200:
            return{
                "city": data["name"],
                "country": data["sys"]["country"],
                "temp": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "humidity": data["main"]["humidity"],
                "description": data["weather"][0]["description"],
                "wind": data["wind"]["speed"]
            }

        
        else:
            print(f"Weather API error: {data.get('message')}")
            print(f"Location searched: {location}")
            return None
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return None

def extract_location(question):
    remove_words = ["weather","watch" ,"what","of", "is", "the", "in", "at",
                    "for", "how", "whats", "like", "today", "current"]
    
    question = question.replace("?", "").replace(".", "").replace("'s", "").replace("'", "")
    words = question.lower().split()
    location = " ".join([w for w in words if w not in remove_words]).strip()

    # if no location, check memory
    if not location:
        memory = load_memory()
        location = memory.get("location") or memory.get("city") or memory.get("home")

    return location
    
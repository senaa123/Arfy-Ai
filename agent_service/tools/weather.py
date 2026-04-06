import os
from dotenv import load_dotenv
from pathlib import Path
import requests

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)
#Read API key 
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

#OpenWeatherMap API endpoint
WEATHER_BASE_URL = os.getenv("WEATHER_BASE_URL")


def get_weather(location: str) -> dict:
    """
    Fetch current weather for a given location.
    """
    #If no API key found
    if not WEATHER_API_KEY:
        return{
            "success": False,
            "message": "Weather API key not found"
        }
    
    try:
        #send Get request toweather API
        response = requests.get(
            WEATHER_BASE_URL,
            params={
                "q": location,
                "appid": WEATHER_API_KEY,
                "units": "metric"       
            },
            timeout=10

        )

        #Raise an error if reqest fails
        response.raise_for_status()

        # Convert JSON response to Python dict
        data = response.json()

        # Extract useful fields
        weather_desc = data["weather"][0]["description"]
        temp = data["main"]["temp"]

        # Return structured result
        return {
            "success": True,
            "location": location,
            "temperature_c": temp,
            "description": weather_desc,
            "message": f"The weather in {location} is {temp}°C with {weather_desc}."
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to fetch weather: {e}"
        }
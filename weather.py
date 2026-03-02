import requests
import os
import string
from memory import load_memory
from dotenv import load_dotenv
from datetime import datetime, timedelta
load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
WEATHER_URL = "http://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "http://api.openweathermap.org/data/2.5/forecast"

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
    
def get_forecast(location, days=5):
    if not WEATHER_API_KEY:
        print("Error: WEATHER_API_KEY is not found.")
        return None
    try:
        response = requests.get(FORECAST_URL, params={
            "q": location,
            "appid": WEATHER_API_KEY,
            "units": "metric",
            "cnt": 40  # max 40 intervals = 5 days
        })
        data = response.json()

        cod = str(data.get("cod", ""))
        if cod not in ["200", "0"]:
            print(f"Forecast API error: {data.get('message')}")
            return None
        
        city = data["city"]["name"]
        country = data["city"]["country"]
        forecasts = {}

        for item in data["list"]:
            dt = datetime.fromtimestamp(item["dt"])
            date_str = dt.strftime("%Y-%m-%d")
            day_name = dt.strftime("%A")  # Monday, Tuesday etc

            if date_str not in forecasts:
                forecasts[date_str] = {
                    "day": day_name,
                    "date": date_str,
                    "temps": [],
                    "descriptions": [],
                    "humidity": [],
                    "wind": []
                }

            forecasts[date_str]["temps"].append(item["main"]["temp"])
            forecasts[date_str]["descriptions"].append(item["weather"][0]["description"])
            forecasts[date_str]["humidity"].append(item["main"]["humidity"])
            forecasts[date_str]["wind"].append(item["wind"]["speed"])


        #summarize each day
        daily_forecasts = []
        for date_str, day_data in list(forecasts.items())[:days]:
            daily_forecasts.append({
                "city": city,
                "country": country,
                "day": day_data["day"],
                "date": day_data["date"],
                "min_temp": round(min(day_data["temps"]), 1),
                "max_temp": round(max(day_data["temps"]), 1),
                "avg_temp": round(sum(day_data["temps"]) / len(day_data["temps"]), 1),
                "description": max(set(day_data["descriptions"]), key=day_data["descriptions"].count),
                "humidity": round(sum(day_data["humidity"]) / len(day_data["humidity"])),
                "wind": round(sum(day_data["wind"]) / len(day_data["wind"]), 1)
            })

        return daily_forecasts

    except Exception as e:
        print(f"Error fetching forecast: {e}")
        return None

def get_day_forecast(location, target_day):
    forecasts = get_forecast(location, days=5)
    if not forecasts:
        return None

    # handle next day tuple
    if isinstance(target_day, tuple):
        _, _, target_date = target_day
        for day in forecasts:
            if day["date"] == target_date:
                return day
        return None

    target_day = target_day.lower().strip()
    for day in forecasts:
        if day["day"].lower() == target_day:
            return day
    return None

def get_tomorrow_forecast(location):
    forecasts = get_forecast(location, days=5)
    if not forecasts:
        return None

    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    for day in forecasts:
        if day["date"] == tomorrow:
            return day
    return None


def extract_location(question):
    
    question_clean = question.lower().translate(str.maketrans('', '', string.punctuation)).strip()
    words = question_clean.split()

    memory = load_memory()
    personal = memory.get("personal", {})

    #familiar loaction word check
    if any (word in question_clean for word in ["hometown", "home town", "home"]):
        return personal.get("hometown")
    
    if any(word in question_clean for word in ["current residence", "residence", "where i live", "where i stay", "i live"]):
        return personal.get("current_residence")
    
    if any(word in question_clean for word in ["my location", "my place", "here"]):
        return personal.get("location")
    
    if "in" in words:
        idx = words.index("in")
        location = " ".join(words[idx + 1:]).strip()
        if location:
            return location

    # check for "for" keyword
    if "for" in words:
        idx = words.index("for")
        location = " ".join(words[idx + 1:]).strip()
        if location:
            return location

    # check for "at" keyword
    if "at" in words:
        idx = words.index("at")
        location = " ".join(words[idx + 1:]).strip()
        if location:
            return location

    # memory fetch 
    location = (
        personal.get("location") or
        personal.get("current_residence") or
        personal.get("hometown")
    )

    return location
    
def is_forecast_question(question):
    """Detect if question is about future weather"""
    forecast_keywords = [
        "tomorrow", "tonight", "this week", "next week",
        "forecast", "monday", "tuesday", "wednesday",
        "thursday", "friday", "saturday", "sunday",
        "next few days", "coming days", "this weekend",
        "weekend", "week"
    ]
    return any(word in question.lower() for word in forecast_keywords)

def extract_target_day(question):
    question_lower = question.lower()
    today = datetime.now()

    # tonight = today
    if "tonight" in question_lower:
        return "tonight"

    # day after tomorrow
    if "day after tomorrow" in question_lower:
        target = today + timedelta(days=2)
        return target.strftime("%A").lower()

    # in X days
    import re
    match = re.search(r'in (\d+) days?', question_lower)
    if match:
        days_ahead = int(match.group(1))
        target = today + timedelta(days=days_ahead)
        return target.strftime("%A").lower()

    # tomorrow
    if "tomorrow" in question_lower:
        return "tomorrow"

    # this week / next few days / coming days
    if any(phrase in question_lower for phrase in [
        "this week", "next few days", "coming days",
        "week", "few days", "next days"
    ]):
        return "week"

    # weekend
    if "weekend" in question_lower:
        return "weekend"

    # next <day> vs this <day>
    days = ["monday", "tuesday", "wednesday", "thursday",
            "friday", "saturday", "sunday"]

    for day in days:
        if day in question_lower:
            # check teher is next
            if "next" in question_lower:

                # find date 
                day_num = days.index(day)
                today_num = today.weekday()
                days_ahead = (day_num - today_num + 7) % 7

                if days_ahead == 0:
                    days_ahead = 7  # next week same day
                target = today + timedelta(days=days_ahead)
                target_date = target.strftime("%Y-%m-%d")

                return ("next", day, target_date)
            
            return day

    return None
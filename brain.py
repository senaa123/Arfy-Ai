import requests
import os
import json
from ddgs import DDGS
from memory import update_memory, get_memory_text, memory_save, load_memory
from weather import extract_location, get_weather, is_forecast_question, extract_target_day, get_tomorrow_forecast, get_forecast, get_day_forecast
from datetime import datetime

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
conversation_history = []

def get_time_context():
    hour = datetime.now().hour
    if hour < 12:
        return "morning"
    elif hour < 14:
        return "afternoon"
    elif hour < 19:
        return "evening"
    else:
        return "night"

def summarize_history(history):
    if len(history) < 10:
        return history
    
    old_messages = history[:6]
    recent_messages = history[6:]

    summary_prompt = f"Summarize this conversation in 2-3 sentences keeping only important facts about Senaa:\n{old_messages}"

    response = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": summary_prompt}]
        }
    )
    summary = response.json()['choices'][0]['message']['content']
    summary_message = {"role": "system", "content": f"Earlier conversation summary: {summary}"}
    return [summary_message] + recent_messages

def search_web(query, max_results=3):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        context = ""
        for i, res in enumerate(results, 1):
            context += f"\nTitle: {res['title']}\nSnippet: {res['body']}\n"
        return context
    except Exception as e:
        print(f"Search Error: {e}")
        return None

def _send_to_groq(weather_prompt, question):
    memory_text = get_memory_text()
    response = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": f"""You are Arfy, Senaa's personal AI assistant. Keep responses short and conversational.
Current time of day: {get_time_context()}

What you know about Senaa:
{memory_text}"""},
                {"role": "user", "content": weather_prompt}
            ]
        }
    )
    answer = response.json()['choices'][0]['message']['content']
    conversation_history.append({"role": "user", "content": question})
    conversation_history.append({"role": "assistant", "content": answer})
    return answer

def ask_brain(question):

    if any(word in question.lower() for word in ["weather", "temperature", "forecast"]):
        location = extract_location(question)

        if not location:
            return "I don't know your location yet. Please tell me where you are."

        if is_forecast_question(question):
            target_day = extract_target_day(question)

            if target_day == "tonight":
                weather_data = get_weather(location)
                if weather_data:
                    weather_prompt = f"""Current weather tonight for {weather_data['city']}, {weather_data['country']}:
- Temperature: {weather_data['temp']}°C, feels like {weather_data['feels_like']}°C
- Condition: {weather_data['description']}
- Humidity: {weather_data['humidity']}%

Give a short friendly summary for tonight like you're talking to Senaa."""
                else:
                    return "Sorry, I couldn't fetch the weather right now."

            elif target_day == "tomorrow":
                forecast = get_tomorrow_forecast(location)
                if forecast:
                    weather_prompt = f"""Tomorrow's weather forecast for {forecast['city']}, {forecast['country']} ({forecast['day']}):
- Temperature: {forecast['min_temp']}°C to {forecast['max_temp']}°C
- Condition: {forecast['description']}
- Humidity: {forecast['humidity']}%
- Wind speed: {forecast['wind']}m/s

Give a short friendly natural summary like you're talking to Senaa.
Suggest what to wear or carry if relevant."""
                else:
                    return "Sorry, I couldn't fetch tomorrow's forecast right now."

            elif target_day == "week":
                forecasts = get_forecast(location, days=5)
                if forecasts:
                    forecast_text = ""
                    for day in forecasts:
                        forecast_text += f"\n{day['day']} ({day['date']}): {day['min_temp']}°C - {day['max_temp']}°C, {day['description']}"
                    weather_prompt = f"""5-day weather forecast for {forecasts[0]['city']}, {forecasts[0]['country']}:
{forecast_text}

Give a short friendly summary of the week's weather like you're talking to Senaa.
Highlight any notable days — good days to go out, rainy days to stay in etc."""
                else:
                    return "Sorry, I couldn't fetch the weekly forecast right now."

            elif target_day == "weekend":
                forecasts = get_forecast(location, days=5)
                if forecasts:
                    weekend = [d for d in forecasts if d["day"] in ["Saturday", "Sunday"]]
                    if weekend:
                        forecast_text = ""
                        for day in weekend:
                            forecast_text += f"\n{day['day']}: {day['min_temp']}°C - {day['max_temp']}°C, {day['description']}"
                        weather_prompt = f"""Weekend weather forecast for {forecasts[0]['city']}, {forecasts[0]['country']}:
{forecast_text}

Give a short friendly summary like you're talking to Senaa.
Is it a good weekend to go out?"""
                    else:
                        return "Sorry, I couldn't find weekend forecast data."
                else:
                    return "Sorry, I couldn't fetch the weekend forecast right now."

            elif isinstance(target_day, tuple):
                forecast = get_day_forecast(location, target_day)
                if forecast:
                    weather_prompt = f"""Weather forecast for next {forecast['day']} for {forecast['city']}, {forecast['country']}:
- Temperature: {forecast['min_temp']}°C to {forecast['max_temp']}°C
- Condition: {forecast['description']}
- Humidity: {forecast['humidity']}%
- Wind speed: {forecast['wind']}m/s

Give a short friendly summary like you're talking to Senaa."""
                else:
                    return "Sorry, that day is outside the 5-day forecast range."

            elif target_day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
                forecast = get_day_forecast(location, target_day)
                if forecast:
                    weather_prompt = f"""{forecast['day']} weather forecast for {forecast['city']}, {forecast['country']}:
- Temperature: {forecast['min_temp']}°C to {forecast['max_temp']}°C
- Condition: {forecast['description']}
- Humidity: {forecast['humidity']}%
- Wind speed: {forecast['wind']}m/s

Give a short friendly natural summary like you're talking to Senaa."""
                else:
                    return "Sorry, that day is outside the 5-day forecast range."

            else:
                # fallback to current weather
                weather_data = get_weather(location)
                if weather_data:
                    weather_prompt = f"""Current weather for {weather_data['city']}, {weather_data['country']}:
- Temperature: {weather_data['temp']}°C, feels like {weather_data['feels_like']}°C
- Condition: {weather_data['description']}
- Humidity: {weather_data['humidity']}%
- Wind speed: {weather_data['wind']}m/s

Give a short friendly natural summary like you're talking to Senaa."""
                else:
                    return "Sorry, I couldn't fetch the weather right now."

        else:
            # current weather
            weather_data = get_weather(location)
            if weather_data:
                weather_prompt = f"""Here is the current weather data for {weather_data['city']}, {weather_data['country']}:
- Temperature: {weather_data['temp']}°C, feels like {weather_data['feels_like']}°C
- Condition: {weather_data['description']}
- Humidity: {weather_data['humidity']}%
- Wind speed: {weather_data['wind']}m/s

Give a short friendly natural summary of this weather like you're talking to Senaa.
Also suggest what to wear or whether to carry an umbrella if relevant."""
            else:
                return "Sorry, I couldn't fetch the weather information right now."

        return _send_to_groq(weather_prompt, question)

    # handle memory correction command
    if "remember" in question and "not" in question:
        parts = question.replace("remember", "").strip().split("not")
        if len(parts) == 2:
            correct = parts[0].strip()
            wrong = parts[1].strip()
            from memory import save_correction
            save_correction(wrong, correct)
            return f"Got it! I'll remember {correct} instead of {wrong}"

    search_keywords = ["news", "today", "latest", "who is", "current", "find out"]
    need_search = any(word in question.lower() for word in search_keywords)

    if need_search:
        print("Searching the web for context...")
        info = search_web(question)
        user_input = f"Question: {question}\n{info}\n\nAnswer using this info"
    else:
        user_input = question

    conversation_history.append({"role": "user", "content": user_input})

    if len(conversation_history) > 10:
        conversation_history[:] = summarize_history(conversation_history)

    memory_text = get_memory_text()

    messages = [{"role": "system", "content": f"""You are Arfy, Senaa's personal AI assistant.
Current time of day: {get_time_context()}

What you know about Senaa:
{memory_text}

If you learn something NEW and IMPORTANT about Senaa, respond normally but add at the end:
MEMORY_UPDATE: {{"category": "personal/preferences/facts", "actual_key": "actual_value"}}

Example:
MEMORY_UPDATE: {{"category": "personal", "current_location": "Eheliyagoda"}}
MEMORY_UPDATE: {{"category": "preferences", "music_platform": "Spotify"}}

Only save things that are:
- Long term facts (job, location, hobbies)
- Strong preferences (likes/dislikes)
- Important routines
DO NOT save temporary things like 'Senaa is tired today'."""}]

    messages.extend(conversation_history)

    response = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        json={"model": "llama-3.3-70b-versatile", "messages": messages}
    )

    answer = response.json()['choices'][0]['message']['content']

    if "MEMORY_UPDATE:" in answer:
        parts = answer.split("MEMORY_UPDATE:")
        answer = parts[0].strip()
        try:
            new_info = json.loads(parts[1].strip())
            category = new_info.pop("category", "facts")

            if "key" in new_info and "value" in new_info:
                key = new_info["key"]
                value = new_info["value"]
                save_data = {key: value}
            else:
                save_data = new_info

            memory = load_memory()
            if category not in memory:
                memory[category] = {}
            memory[category].update(save_data)
            memory_save(memory)
            print(f"Memory updated in '{category}': {save_data}")
        except Exception as e:
            print(f"Memory save error: {e}")

    conversation_history.append({"role": "assistant", "content": answer})
    return answer
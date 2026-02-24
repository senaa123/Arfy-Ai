import requests
import os
import json
from ddgs import DDGS
from memory import update_memory, get_memory_text, memory_save, load_memory
from weather import extract_location, get_weather
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

def ask_brain(question):

    if any(word in question.lower() for word in ["weather", "temperature", "forecast"]):
        location = extract_location(question)

        if location:
            weather_data = get_weather(location)
            if weather_data:
                weather_prompt = f"""Here is the current weather data for {weather_data['city']}, {weather_data['country']}:
- Temperature: {weather_data['temp']}°C, feels like {weather_data['feels_like']}°C
- Condition: {weather_data['description']}
- Humidity: {weather_data['humidity']}%
- Wind speed: {weather_data['wind']}m/s

Give a short friendly natural summary of this weather like you're talking to Senaa.
Also suggest what to wear or whether to carry an umbrella if relevant."""

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
            else:
                return "Sorry, I couldn't fetch the weather information right now."
        else:
            return "I don't know your location yet. Please tell me where you are."

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

    # summarize instead of dropping old messages
    if len(conversation_history) > 10:
        conversation_history[:] = summarize_history(conversation_history)

    memory_text = get_memory_text()

    messages = [{"role": "system", "content": f"""You are Arfy, Senaa's personal AI assistant.
Current time of day: {get_time_context()}

What you know about Senaa:
{memory_text}

If you learn something NEW and IMPORTANT about Senaa, respond normally but add at the end:
MEMORY_UPDATE: {{"category": "personal/preferences/facts", "key": "value"}}

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
            memory = load_memory()
            if category not in memory:
                memory[category] = {}
            memory[category].update(new_info)
            memory_save(memory)
            print(f"Memory updated in '{category}': {new_info}")
        except:
            pass

    conversation_history.append({"role": "assistant", "content": answer})
    return answer
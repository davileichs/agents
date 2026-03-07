import os
import requests

def open_weather(city: str) -> str:
    """Fetches the current weather for a city using OpenWeather API."""
    api_key = os.environ.get("OPEN_WEATHER_KEY")
    if not api_key:
        return "Error: OPEN_WEATHER_KEY environment variable is not set."
        
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    try:
        response = requests.get(url)
        data = response.json()
        
        if response.status_code == 200:
            temp = data["main"]["temp"]
            desc = data["weather"][0]["description"]
            return f"The current weather in {city} is {temp}°C with {desc}."
        else:
            message = data.get("message", "Unknown error")
            return f"Error fetching weather: {message}"
    except Exception as e:
        return f"Request failed: {str(e)}"

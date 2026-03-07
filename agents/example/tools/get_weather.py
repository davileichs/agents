def get_weather(location: str) -> str:
    """Returns the weather for a given location."""
    # mock weather response
    if "tokio" in location.lower() or "tokyo" in location.lower():
        return "It is currently 25°C and sunny in Tokyo."
    if "london" in location.lower():
        return "It is currently 15°C and raining in London."
    return f"It is currently 20°C and cloudy in {location}."

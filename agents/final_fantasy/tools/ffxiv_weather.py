import logging
from typing import Dict, Any
from legacy.core.services.final_fantasy_api import FinalFantasyAPI

logger = logging.getLogger(__name__)

async def ffxiv_weather(**kwargs) -> Dict[str, Any]:
    """Retrieve weather forecast for a specific FFXIV zone."""
    try:
        zone: str = kwargs.get("zone")
        
        if not zone or not isinstance(zone, str):
            return {
                "success": False,
                "error": "Zone parameter is required and must be a string",
                "zone": zone
            }
        
        ff_api = FinalFantasyAPI()
        weather_data = await ff_api.get_weather(zone)
        
        if weather_data:
            return {
                "success": True,
                "zone": zone,
                "forecast": weather_data
            }
        else:
            return {
                "success": False,
                "message": "No weather data found for zone",
                "zone": zone
            }
            
    except Exception as e:
        logger.error(f"Error getting FFXIV weather: {e}")
        return {
            "success": False,
            "error": str(e),
            "zone": kwargs.get("zone")
        }

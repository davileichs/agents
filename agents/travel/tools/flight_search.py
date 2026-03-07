import aiohttp
import asyncio
import json
import os
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

async def flight_search(**kwargs) -> Dict[str, Any]:
    """Search for flights using SerpApi Google Flights engine."""
    api_key = os.environ.get("SERPAPI_API_KEY")
    ENDPOINT = "https://serpapi.com/search?engine=google_flights"
    
    if not api_key:
        return {"error": "SERPAPI_API_KEY not configured", "success": False}
        
    try:
        # Check if doing a multi-city search
        multi_city = kwargs.get('multi_city')
        if multi_city:
            # Type 3 is implied for multi_city logic here
            currency = kwargs.get('currency', 'USD')
            include_airlines = kwargs.get('include_airlines')
            multi_city_json = json.dumps(multi_city)
            
            params = {
                'multi_city_json': multi_city_json,
                'type': 3,
                'currency': currency,
                'api_key': api_key
            }
            if include_airlines:
                params['include_airlines'] = ','.join(include_airlines)
                
            logger.info(f"Searching multi-city flights: {len(multi_city)} segments")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(ENDPOINT, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "success": True,
                            "results": data,
                            "search_params": {
                                "multi_city": multi_city,
                                "currency": currency,
                                "type": 3
                            }
                        }
                    else:
                        return {
                            "error": f"API request failed with status {response.status}",
                            "success": False
                        }
        
        # Regular round trip or one way
        departure: Optional[str] = kwargs.get('departure')
        arrival: str = kwargs.get('arrival')
        outbound_date: str = kwargs.get('outbound_date')
        return_date: Optional[str] = kwargs.get('return_date')
        currency: str = kwargs.get('currency', 'USD')
        include_airlines: Optional[List[str]] = kwargs.get('include_airlines')
        type: int = int(kwargs.get('type', 1))
        user_id: Optional[str] = kwargs.get('user_id')
        
        if (not departure) and user_id:
            try:
                from legacy.core.services.travel_profile_store import travel_profile_store
                stored = travel_profile_store.get_default_departure(str(user_id))
                if stored:
                    departure = stored
            except Exception:
                pass
        
        if type == 1:
            if not return_date:
                return {
                    "error": "Return date is required for round trip flights",
                    "success": False
                }
            params = {
                'departure_id': departure,
                'arrival_id': arrival,
                'outbound_date': outbound_date,
                'return_date': return_date,
                'currency': currency,
                'type': type,
                'api_key': api_key
            }
        elif type == 2:
            params = {
                'departure_id': departure,
                'arrival_id': arrival,
                'outbound_date': outbound_date,
                'currency': currency,
                'type': type,
                'api_key': api_key
            }
        else:
            return {
                "error": "Invalid flight type. Use 1 for round trip, 2 for one way",
                "success": False
            }
            
        if include_airlines:
            params['include_airlines'] = ','.join(include_airlines)
        
        logger.info(f"Searching flights: {departure} -> {arrival} on {outbound_date}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(ENDPOINT, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "results": data,
                        "search_params": {
                            "departure": departure,
                            "arrival": arrival,
                            "outbound_date": outbound_date,
                            "return_date": return_date,
                            "currency": currency,
                            "type": type
                        }
                    }
                else:
                    return {
                        "error": f"API request failed with status {response.status}",
                        "success": False
                    }
                    
    except Exception as e:
        logger.error(f"Error searching flights: {e}")
        return {
            "error": str(e),
            "success": False
        }

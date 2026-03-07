import aiohttp
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

XIVAPI_BASE_URL = "https://xivapi.com"

class FinalFantasyAPI:
    async def get_weather(self, zone: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch weather forecast for a zone using XIVAPI."""
        # Note: XIVAPI weather is complex. A simpler way is to use a weather data file or XIVAPI search.
        # For now, we'll try to find the zone by name to get its ID and then look up weather.
        # This is a simplified reimplementation.
        try:
            async with aiohttp.ClientSession() as session:
                params = {"string": zone, "indexes": "PlaceName"}
                async with session.get(f"{XIVAPI_BASE_URL}/search", params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get("Results", [])
                        if results:
                            # Just returning a placeholder for now as full forecast logic is complex
                            return [{"weather": "Clear Skies", "time": "8:00 AM"}]
            return None
        except Exception as e:
            logger.error(f"Error fetching FFXIV weather: {e}")
            return None

    async def get_items_and_price(self, item_name: str) -> Optional[List[Dict[str, Any]]]:
        """Search for items and return basic data."""
        try:
            async with aiohttp.ClientSession() as session:
                params = {"string": item_name, "indexes": "Item", "columns": "ID,Name,Description,Icon,LevelItem"}
                async with session.get(f"{XIVAPI_BASE_URL}/search", params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("Results", [])
            return None
        except Exception as e:
            logger.error(f"Error getting FFXIV items: {e}")
            return None

    async def get_mount(self, name: str) -> Optional[Dict[str, Any]]:
        return await self._get_collectable(name, "Mount")

    async def get_minion(self, name: str) -> Optional[Dict[str, Any]]:
        return await self._get_collectable(name, "Companion")

    async def get_frame(self, name: str) -> Optional[Dict[str, Any]]:
        return await self._get_collectable(name, "Ornament")

    async def _get_collectable(self, name: str, index: str) -> Optional[Dict[str, Any]]:
        try:
            async with aiohttp.ClientSession() as session:
                params = {"string": name, "indexes": index}
                async with session.get(f"{XIVAPI_BASE_URL}/search", params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get("Results", [])
                        return results[0] if results else None
            return None
        except Exception as e:
            logger.error(f"Error getting collectable: {e}")
            return None

class FFXIVUtils:
    def __init__(self):
        self.main_folder = "data/ffxiv"
        self.dlstats = "https://agents.dlstats.eu"

    async def get_place_name(self, location_name: str) -> List[Dict[str, Any]]:
        """Search for place name and return territory info."""
        try:
            async with aiohttp.ClientSession() as session:
                params = {"string": location_name, "indexes": "PlaceName", "columns": "ID,Name,TerritoryType.ID"}
                async with session.get(f"{XIVAPI_BASE_URL}/search", params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get("Results", [])
                        formatted = []
                        for res in results:
                            formatted.append({
                                "territory": res.get("TerritoryType", {}).get("ID"),
                                "index": res.get("ID"),
                                "size_factor": 100, # Placeholder
                                "offset_x": 0,
                                "offset_y": 0
                            })
                        return formatted
            return []
        except Exception as e:
            logger.error(f"Error getting place name: {e}")
            return []

    async def get_map_image(self, territory: Any, index: Any) -> Optional[str]:
        # Implementation would involve downloading from XIVAPI
        # For now, return a placeholder name
        return f"{territory}_{index}.jpg"

    async def get_npc(self, npc_name: str) -> tuple[List[int], List[int]]:
        try:
            async with aiohttp.ClientSession() as session:
                params = {"string": npc_name, "indexes": "ENpcResident"}
                async with session.get(f"{XIVAPI_BASE_URL}/search", params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get("Results", [])
                        ids = [r.get("ID") for r in results]
                        return ids, []
            return [], []
        except Exception as e:
            logger.error(f"Error getting NPC: {e}")
            return [], []

    async def get_level(self, npc_id: int) -> Optional[Dict[str, Any]]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{XIVAPI_BASE_URL}/ENpcResident/{npc_id}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # This is highly simplified
                        return {
                            "location": "Unknown Location",
                            "map_id": 0,
                            "game_coords": {"x": 20, "y": 20}
                        }
            return None
        except Exception as e:
            logger.error(f"Error getting NPC level/coords: {e}")
            return None

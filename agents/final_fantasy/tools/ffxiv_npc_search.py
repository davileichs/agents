import logging
from typing import Optional, Dict, Any, List
from legacy.core.tools.ffxiv import FFXIVUtils
from agents.final_fantasy.tools.ffxiv_map import _map_mgr

logger = logging.getLogger(__name__)

class FFXIVNPCSearchManager:
    def __init__(self):
        self.ff = FFXIVUtils()
        self.map_mgr = _map_mgr
        
    async def search(self, npc_name: str, location_name: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        try:
            if not npc_name:
                return {"success": False, "error": "NPC name is required"}
            
            npcs = await self._get_location_by_npc_name(npc_name)

            if not location_name:
                if len(npcs) == 1:
                    location_name = npcs[0]['location']
                elif len(npcs) > 1:
                    location_names_set = set()
                    for data in npcs:
                        if data.get('location'):
                            location_names_set.add(data['location'])
                    location_names = list(location_names_set)
                    return {
                        "success": True,
                        "message": f"NPC '{npc_name}' found with {len(location_names)} unique location(s)",
                        "npc_name": npc_name,
                        "total_locations": len(location_names),
                        "locations": location_names,
                        "action_required": "Please specify a location_name to get a marked map"
                    }
                else:
                    return {"success": False, "message": f"NPC {npc_name} found but no location name found"}

            map_data = await self._get_map_by_npc(npcs, location_name)
            
            if not map_data:
                return {"success": False, "message": f"NPC {npc_name} found but no Map data found.", "npc_name": npc_name}

            return {"success": True, "npc_name": npc_name, "map": map_data}
            
        except Exception as e:
            logger.error(f"Error in NPC Search: {e}")
            return {"success": False, "message": f"An error occurred: {str(e)}"}

    async def _get_location_by_npc_name(self, npc_name: str) -> List[Dict[str, Any]]:
        try:
            npc_ids, map_ids = await self.ff.get_npc(npc_name)
            npcs = []
            for npc_id in npc_ids:
                npc_level = await self.ff.get_level(npc_id)
                if npc_level and npc_level.get('game_coords'):
                    coords = npc_level['game_coords']
                    if coords and coords.get('x') is not None and coords.get('y') is not None:
                        data = {
                            'npc_id': npc_id,
                            'location': npc_level['location'],
                            'map_id': npc_level['map_id'],
                            'coords': coords,
                            'npc_level': npc_level
                        }
                        npcs.append(data)
            return npcs
        except Exception as e:
            logger.error(f"Error in _get_location_by_npc_name: {e}")
            return []

    async def _get_map_by_npc(self, npcs: List[Dict[str, Any]], location_name: str) -> Dict[str, Any]:
        try:
            map_data = {}
            processed_coords = []
            
            for npc_data in npcs:
                if npc_data.get('location') == location_name:
                    coords = npc_data['coords']
                    x, y = coords.get('x'), coords.get('y')
                    
                    should_process = True
                    for processed_x, processed_y in processed_coords:
                        distance = ((x - processed_x) ** 2 + (y - processed_y) ** 2) ** 0.5
                        if distance <= 2:
                            should_process = False
                            break
                    
                    if should_process:
                        result = await self.map_mgr.get_map(
                            location_name=location_name,
                            x_coordinate=x,
                            y_coordinate=y,
                            mark_coordinates=True
                        )
                        
                        if result.get('success'):
                            map_data[npc_data['npc_id']] = result
                            processed_coords.append((x, y))
            return map_data
        except Exception as e:
            logger.error(f"Error in _get_map_by_npc: {e}")
            return {}

_npc_mgr = FFXIVNPCSearchManager()

async def ffxiv_npc_search(**kwargs) -> Dict[str, Any]:
    """Search for NPCs in Final Fantasy XIV and optionally generate map markers."""
    npc_name: str = kwargs.get("npc_name", "")
    location_name: Optional[str] = kwargs.get("location_name")
    limit: Optional[int] = kwargs.get("limit")
    
    return await _npc_mgr.search(npc_name, location_name, limit)

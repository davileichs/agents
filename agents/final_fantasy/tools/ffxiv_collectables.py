import logging
from typing import Dict, Any
from app.services.ffxiv import FinalFantasyAPI

logger = logging.getLogger(__name__)

async def ffxiv_collectables(**kwargs) -> Dict[str, Any]:
    """Retrieve information about FFXIV collectables like mounts, minions, and frames."""
    try:
        name: str = kwargs.get("name")
        collectable_type: str = kwargs.get("collectable_type", "mount")
        
        if not name or not isinstance(name, str):
            return {
                "success": False,
                "error": "Name parameter is required and must be a string",
                "name": name
            }
            
        ff_api = FinalFantasyAPI()
        
        if collectable_type == "mount":
            data = await ff_api.get_mount(name)
        elif collectable_type == "minion":
            data = await ff_api.get_minion(name)
        elif collectable_type == "frame":
            data = await ff_api.get_frame(name)
        else:
            return {
                "success": False,
                "error": "Invalid collectable type. Use: mount, minion, or frame"
            }
        
        if data:
            return {
                "success": True,
                "name": name,
                "type": collectable_type,
                "data": data
            }
        else:
            return {
                "success": False,
                "message": f"No {collectable_type} found with name: {name}",
                "name": name,
                "type": collectable_type
            }
            
    except Exception as e:
        logger.error(f"Error getting FFXIV collectables: {e}")
        return {
            "success": False,
            "error": str(e),
            "name": kwargs.get("name"),
            "type": kwargs.get("collectable_type", "mount")
        }

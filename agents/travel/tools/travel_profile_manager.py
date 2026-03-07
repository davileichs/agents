from typing import Dict, Any, Optional
import logging
from app.services.travel_service import travel_service

logger = logging.getLogger(__name__)

async def travel_profile_manager(**kwargs) -> Dict[str, Any]:
    """Manage travel profile for a user (set/get default departure city)."""
    try:
        action: str = (kwargs.get("action") or "get").lower()
        user_id: Optional[str] = kwargs.get("user_id")
        departure: Optional[str] = kwargs.get("departure")

        if not user_id:
            return {"success": False, "error": "user_id is required"}

        if action == "set":
            if not departure:
                return {"success": False, "error": "departure is required for set action"}
            await travel_service.set_default_departure(user_id, departure)
            return {"success": True, "message": "Default departure updated", "departure": departure}

        if action == "get":
            saved = await travel_service.get_default_departure(user_id)
            return {"success": True, "departure": saved}

        if action == "delete":
            ok = await travel_service.delete_profile(user_id)
            return {"success": True, "deleted": ok}

        return {"success": False, "error": f"Invalid action: {action}"}
    except Exception as e:
        logger.error(f"Error in Travel profile manager: {e}")
        return {"success": False, "error": str(e)}

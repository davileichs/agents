import logging
from typing import Dict, Any
from app.services.ffxiv import FinalFantasyAPI

logger = logging.getLogger(__name__)

async def ffxiv_items(**kwargs) -> Dict[str, Any]:
    """Retrieve items and their prices from the Final Fantasy XIV database."""
    try:
        item_name: str = kwargs.get("item_name")
        
        if not item_name or not isinstance(item_name, str):
            return {
                "success": False,
                "error": "Item name parameter is required and must be a string",
                "item_name": item_name
            }
        
        ff_api = FinalFantasyAPI()
        items_data = await ff_api.get_items_and_price(item_name)
        
        if items_data:
            return {
                "success": True,
                "item_name": item_name,
                "items": items_data
            }
        else:
            return {
                "success": False,
                "message": "No item data found",
                "item_name": item_name
            }
            
    except Exception as e:
        logger.error(f"Error getting FFXIV item data: {e}")
        return {
            "success": False,
            "error": str(e),
            "item_name": kwargs.get("item_name")
        }

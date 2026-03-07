import logging
import re
import json
from typing import Dict, Any, Optional

import aiohttp
from sqlalchemy import select
from app.services.database import AsyncSessionLocal
from app.models.token import Token

logger = logging.getLogger(__name__)

BASE_API_URL = "https://keeptripplansimple.com/api/external/trips"

class KTPSManager:
    def __init__(self):
        self.token = ''

    async def _load_token(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        try:
            user_id = self._resolve_user_id(kwargs)
            if not user_id:
                return {"success": False, "error": "user_id is required"}
            
            async with AsyncSessionLocal() as session:
                stmt = select(Token).where(
                    (Token.user_id == user_id) & 
                    (Token.service == "ktps")
                )
                result = await session.execute(stmt)
                token_record = result.scalar_one_or_none()
                
                if not token_record:
                    return {"success": False, "error": "User configuration not found. Please save your KTPS token first."}
                
                self.token = token_record.token
                
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return {"success": False, "error": str(e)}
        return {"success": True}
    
    async def _add_user(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        try:
            user_id = self._resolve_user_id(kwargs)
            token_str = kwargs.get("token")
            if not all([user_id, token_str]):
                return {"success": False, "error": "user_id and token are required"}
            
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    stmt = select(Token).where(
                        (Token.user_id == user_id) & 
                        (Token.service == "ktps")
                    )
                    result = await session.execute(stmt)
                    existing = result.scalar_one_or_none()
                    
                    if existing:
                        existing.token = token_str
                    else:
                        new_token = Token(
                            user_id=user_id,
                            service="ktps",
                            token=token_str
                        )
                        session.add(new_token)
            
            return {"success": True, "message": "KTPS user token added successfully", "user_id": user_id}
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return {"success": False, "error": str(e)}

    def _resolve_user_id(self, kwargs: Dict[str, Any]) -> Optional[str]:
        user_id = kwargs.get("user_id")
        if user_id:
            return str(user_id)

    async def _fetch_url(self, url: str) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 401:
                        return {"success": False, "error": "Invalid or expired token", "status": 401}
                    if response.status != 200:
                        return {"success": False, "error": f"Request failed with status {response.status}", "status": response.status}
                    text = await response.text()
                    try:
                        return {"success": True, "data": json.loads(text)}
                    except json.JSONDecodeError:
                        return {"success": True, "data": {"raw": text}}
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return {"success": False, "error": str(e)}

    async def _post_url(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 401:
                        return {"success": False, "error": "Invalid or expired token", "status": 401}
                    if response.status != 200:
                        text = await response.text()
                        return {"success": False, "error": f"Request failed with status {response.status}: {text}", "status": response.status}
                    text = await response.text()
                    try:
                        return {"success": True, "data": json.loads(text)}
                    except json.JSONDecodeError:
                        return {"success": True, "data": {"raw": text}}
        except Exception as e:
            logger.error(f"Error posting to {url}: {e}")
            return {"success": False, "error": str(e)}

    async def _list_trips(self) -> Dict[str, Any]:
        logger.info(f"Fetching trips list from {BASE_API_URL}")
        fetch_result = await self._fetch_url(BASE_API_URL)
        if not fetch_result.get("success"):
            return fetch_result
        data = fetch_result.get("data", {})
        trips = data if isinstance(data, list) else data.get("trips", [])
        return {"success": True, "trips": trips}

    async def _chat(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        trip_id = kwargs.get("trip_id")
        if not trip_id:
            return {"success": False, "error": "You must provide a 'trip_id' to chat about a specific trip."}
            
        message = kwargs.get("message")
        if not message:
            return {"success": False, "error": "You must provide a 'message' string for the chat action."}
            
        user_id = self._resolve_user_id(kwargs)
        session_id = user_id or "user1"
            
        chat_url = BASE_API_URL.replace('/trips', '/chat-memory')
        payload = {"travelId": trip_id, "message": message, "sessionId": session_id}
        
        logger.info(f"Sending chat request to {chat_url} for trip {trip_id}")
        return await self._post_url(chat_url, payload)


# Use a global instance to keep DB access single-instance for this module
_manager = KTPSManager()

async def keeptripplansimple(**kwargs) -> Dict[str, Any]:
    """Connect to Keep Trip Plan Simple and fetch/chat trip data."""
    try:
        action = (kwargs.get("action") or "list_trips").lower()

        if action == "save_token":                
            return await _manager._add_user(kwargs)
        
        load_result = await _manager._load_token(kwargs)
        if not load_result.get("success"):
            return load_result
        
        if not _manager.token:
            return {
                "success": False,
                "error": "No token provided. Please add your KTPS token first",
            }

        if action == "list_trips":
            return await _manager._list_trips()

        if action == "chat":
            return await _manager._chat(kwargs)
        
        return {"success": False, "error": f"Invalid action: {action}"}

    except Exception as e:
        logger.error(f"Error in keeptripplansimple tool: {e}")
        return {"success": False, "error": str(e)}

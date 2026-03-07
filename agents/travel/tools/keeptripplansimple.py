import logging
import re
import json
from pathlib import Path
from typing import Dict, Any, Optional

import aiohttp
from tinydb import Query, TinyDB

logger = logging.getLogger(__name__)

BASE_API_URL = "https://keeptripplansimple.com/api/external/trips"

class KTPSManager:
    def __init__(self):
        self.token = ''
        self.trip_id = ''
        self._init_db()

    def _init_db(self):
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        self.db = TinyDB(data_dir / "ktps_tokens.json")
        self.users_table = self.db.table("users")
        self.User = Query()

    async def _load_token(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        try:
            user_id = self._resolve_user_id(kwargs)
            channel_id = self._resolve_channel_id(kwargs, user_id)
            if not all([user_id, channel_id]):
                return {"success": False, "error": "user_id and channel_id are required"}
            user = self.users_table.search((self.User.user_id == user_id) & (self.User.channel_id == channel_id))
            if not user:
                return {"success": False, "error": "User configuration not found"}
            user_data = user[0].copy()
            self.token = user_data.get("token", "")
            self.trip_id = user_data.get("trip_id", "")
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return {"success": False, "error": str(e)}
        return {"success": True}
    
    async def _add_user(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        try:
            user_id = self._resolve_user_id(kwargs)
            channel_id = self._resolve_channel_id(kwargs, user_id)
            token = kwargs.get("token")
            if not all([user_id, channel_id, token]):
                return {"success": False, "error": "user_id, channel_id, and token are required"}
            
            existing = self.users_table.search((self.User.user_id == user_id) & (self.User.channel_id == channel_id))
            user_data = {"user_id": user_id, "channel_id": channel_id, "token": token}
            
            if existing:
                existing_data = existing[0]
                if "trip_id" in existing_data:
                    user_data["trip_id"] = existing_data["trip_id"]
                doc_id = self.users_table.update(user_data, (self.User.user_id == user_id) & (self.User.channel_id == channel_id))
            else:
                doc_id = self.users_table.insert(user_data)
            return {"success": True, "message": "KTPS user token added successfully", "user_id": user_id, "channel_id": channel_id, "doc_id": doc_id}
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return {"success": False, "error": str(e)}

    def _resolve_user_id(self, kwargs: Dict[str, Any]) -> Optional[str]:
        user_id = kwargs.get("user_id")
        if user_id:
            return str(user_id)
        session_id = kwargs.get("session_id")
        if not session_id:
            return None
        try:
            from legacy.core.message_history import message_history
            user_from_history = message_history.get_session_user_id(session_id)
            if user_from_history:
                return str(user_from_history)
        except Exception as e:
            logger.warning(f"Could not resolve user_id from message history: {e}")
            
        patterns = [r"^discord_private_(\d+)$", r"^telegram_user_(\d+)$", r"^discord_channel_(\d+)$", r"^telegram_chat_(\d+)$"]
        for pattern in patterns:
            m = re.match(pattern, session_id)
            if m:
                return m.group(1)
        return session_id

    def _resolve_channel_id(self, kwargs: Dict[str, Any], resolved_user_id: Optional[str]) -> Optional[str]:
        channel_id = kwargs.get("channel_id")
        if channel_id:
            return str(channel_id)
        session_id = kwargs.get("session_id")
        if not session_id:
            return None
        m = re.match(r"^discord_channel_(\d+)$", session_id)
        if m:
            return m.group(1)
        m = re.match(r"^telegram_chat_(\d+)$", session_id)
        if m:
            return m.group(1)
        m = re.match(r"^(discord_private|telegram_user)_(\d+)$", session_id)
        if m:
            return f"{m.group(1)}_{m.group(2)}"
        return session_id

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
        provided_trip_id = kwargs.get("trip_id")
        trip_id = provided_trip_id or self.trip_id
        
        if provided_trip_id and provided_trip_id != self.trip_id:
            try:
                user_id = self._resolve_user_id(kwargs)
                channel_id = self._resolve_channel_id(kwargs, user_id)
                if user_id and channel_id:
                    self.users_table.update({"trip_id": trip_id}, (self.User.user_id == user_id) & (self.User.channel_id == channel_id))
                    self.trip_id = trip_id
                    logger.info(f"Saved trip {trip_id} for user {user_id}")
            except Exception as e:
                logger.error(f"Error saving trip_id: {e}")

        if not trip_id:
            return {"success": False, "error": "No trip_id is saved. Please use 'list_trips' to find a trip, then provide its 'trip_id' in the 'chat' action."}
            
        message = kwargs.get("message")
        if not message:
            return {"success": False, "error": "You must provide a 'message' (string) for the chat action."}
            
        user_id = self._resolve_user_id(kwargs)
        channel_id = self._resolve_channel_id(kwargs, user_id)
        session_id = channel_id or "user1"
            
        chat_url = BASE_API_URL.replace('/trips', '/chat-memory')
        payload = {"travelId": trip_id, "message": message, "sessionId": session_id}
        
        logger.info(f"Sending chat request to {chat_url} for trip {trip_id} (session {session_id})")
        return await self._post_url(chat_url, payload)


# Use a global instance to keep DB access single-instance for this module
_manager = KTPSManager()

async def keeptripplansimple(**kwargs) -> Dict[str, Any]:
    """Connect to Keep Trip Plan Simple and fetch/chat trip data."""
    try:
        action = (kwargs.get("action") or "list_trips").lower()

        if action == "save_token":                
            return await _manager._add_user(kwargs)
        
        await _manager._load_token(kwargs)
        
        if not _manager.token:
            return {
                "success": False,
                "error": "No token/share link provided. Request to add token first",
            }

        if action == "list_trips":
            return await _manager._list_trips()

        if action == "get_trip":
            return {"success": False, "error": "The 'get_trip' action is removed. Please use 'list_trips' to find a trip, then 'chat' with the trip_id to start talking about it."}
        
        if action == "chat":
            return await _manager._chat(kwargs)
        
        if action == "get_trip_details":
            return {"success": False, "error": "The 'get_trip_details' action is deprecated. Please use the 'chat' action to ask questions about the trip instead."}

        return {"success": False, "error": f"Invalid action: {action}"}

    except Exception as e:
        logger.error(f"Error in keeptripplansimple tool: {e}")
        return {"success": False, "error": str(e)}

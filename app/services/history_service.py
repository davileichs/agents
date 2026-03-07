from typing import List, Dict, Any
from sqlalchemy import select, desc
from app.services.database import AsyncSessionLocal
from app.models.message import Message

class HistoryService:
    async def get_recent_history(self, user_id: str, agent_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves history for a user/agent pair, returned in chronological order."""
        if not user_id:
            return []
            
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Message)
                .where(Message.user_id == user_id, Message.agent_name == agent_name)
                .order_by(desc(Message.created_at), desc(Message.id))
                .limit(limit)
            )
            result = await session.execute(stmt)
            messages = result.scalars().all()
            
            # Convert to dicts and reverse to get chronological order
            return [m.to_dict() for m in reversed(messages)]

    async def add_messages(self, user_id: str, agent_name: str, messages: List[Dict[str, Any]]):
        """Saves a list of message dicts to the database."""
        if not user_id or not messages:
            return
            
        async with AsyncSessionLocal() as session:
            async with session.begin():
                for msg in messages:
                    db_msg = Message(
                        user_id=user_id,
                        agent_name=agent_name,
                        role=msg.get("role"),
                        content=msg.get("content"),
                        tool_call_id=msg.get("tool_call_id"),
                        tool_calls=msg.get("tool_calls"),
                        name=msg.get("name")
                    )
                    session.add(db_msg)
                await session.commit()

history_service = HistoryService()

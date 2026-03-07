from datetime import datetime
from typing import Optional, Any
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Index
from app.services.database import Base

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    agent_name = Column(String, nullable=False)
    role = Column(String, nullable=False) # system, user, assistant, tool
    content = Column(Text, nullable=True)
    tool_call_id = Column(String, nullable=True)
    tool_calls = Column(JSON, nullable=True)
    name = Column(String, nullable=True) # for tool role
    created_at = Column(DateTime, default=datetime.utcnow)

    # Indexes for fast lookup of history
    __table_args__ = (
        Index("idx_user_agent_history", "user_id", "agent_name", "created_at"),
    )

    def to_dict(self) -> dict:
        d = {
            "role": self.role,
            "content": self.content,
        }
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.name:
            d["name"] = self.name
        return d

from sqlalchemy import Column, Integer, String, UniqueConstraint
from app.services.database import Base

class Token(Base):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    service = Column(String, index=True, nullable=False)
    token = Column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'service', name='uix_user_service'),
    )

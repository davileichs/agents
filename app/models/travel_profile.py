from sqlalchemy import Column, Integer, String, UniqueConstraint
from app.services.database import Base

class TravelProfile(Base):
    __tablename__ = "travel_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    default_departure = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint('user_id', name='uix_travel_profile_user_id'),
    )

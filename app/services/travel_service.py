import logging
from typing import Optional
from sqlalchemy import select
from app.services.database import AsyncSessionLocal
from app.models.travel_profile import TravelProfile

logger = logging.getLogger(__name__)

class TravelProfileService:
    @staticmethod
    async def get_default_departure(user_id: str) -> Optional[str]:
        async with AsyncSessionLocal() as session:
            stmt = select(TravelProfile).where(TravelProfile.user_id == user_id)
            result = await session.execute(stmt)
            profile = result.scalar_one_or_none()
            return profile.default_departure if profile else None

    @staticmethod
    async def set_default_departure(user_id: str, departure: str) -> None:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                stmt = select(TravelProfile).where(TravelProfile.user_id == user_id)
                result = await session.execute(stmt)
                profile = result.scalar_one_or_none()
                
                if profile:
                    profile.default_departure = departure
                else:
                    new_profile = TravelProfile(user_id=user_id, default_departure=departure)
                    session.add(new_profile)

    @staticmethod
    async def delete_profile(user_id: str) -> bool:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                stmt = select(TravelProfile).where(TravelProfile.user_id == user_id)
                result = await session.execute(stmt)
                profile = result.scalar_one_or_none()
                
                if profile:
                    await session.delete(profile)
                    return True
                return False

travel_service = TravelProfileService()

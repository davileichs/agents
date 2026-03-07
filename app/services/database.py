import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

# Neon PostgreSQL often requires sslmode=require
db_url = settings.database_url
connect_args = {}

if db_url and db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    parsed = urlparse(db_url)
    query = parse_qs(parsed.query)
    
    # Handle sslmode
    if "sslmode" in query:
        if query["sslmode"][0] == "require":
            connect_args["ssl"] = True
        del query["sslmode"]
    
    # Handle channel_binding which asyncpg doesn't support
    if "channel_binding" in query:
        del query["channel_binding"]
        
    # Reconstruct URL without problematic params
    new_query = urlencode(query, doseq=True)
    db_url = urlunparse(parsed._replace(query=new_query))

# Create async engine
engine = create_async_engine(
    db_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
    connect_args=connect_args
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def get_db():
    """Dependency for getting async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

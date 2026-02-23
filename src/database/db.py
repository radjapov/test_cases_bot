from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.config import settings
from src.database.models import Base

# Create async engine
engine = create_async_engine(settings.database_url, future=True, echo=False)

# Create sessionmaker
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    """Initializes the database and creates tables if they don't exist."""
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # Use for dropping tables during development
        await conn.run_sync(Base.metadata.create_all)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection to get a database session."""
    async with async_session() as session:
        yield session

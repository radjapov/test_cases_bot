from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.database.models import User, Generation

# === User CRUD ===

async def get_or_create_user(session: AsyncSession, telegram_id: int, username: Optional[str] = None, first_name: Optional[str] = None) -> User:
    """Gets a user by telegram_id, or creates a new one if not found."""
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user

async def update_user_settings(session: AsyncSession, telegram_id: int, output_format: Optional[str] = None, template_type: Optional[str] = None) -> Optional[User]:
    """Updates user's settings."""
    user = await get_or_create_user(session, telegram_id)
    if not user:
        return None
        
    if output_format:
        user.output_format = output_format
    if template_type:
        user.template_type = template_type
    
    await session.commit()
    await session.refresh(user)
    return user


# === Generation CRUD ===

async def create_generation(session: AsyncSession, user_id: int, raw_text: str, generated_test_cases: str, output_format: str, template_type: str) -> Generation:
    """Creates a new generation record."""
    generation = Generation(
        user_id=user_id,
        raw_text=raw_text,
        generated_test_cases=generated_test_cases,
        output_format=output_format,
        template_type=template_type,
    )
    session.add(generation)
    await session.commit()
    await session.refresh(generation)
    return generation


async def get_user_generations(session: AsyncSession, telegram_id: int, limit: int = 5) -> List[Generation]:
    """Gets the last N generations for a user."""
    stmt = (
        select(Generation)
        .join(User)
        .where(User.telegram_id == telegram_id)
        .order_by(Generation.created_at.desc())
        .limit(limit)
        .options(selectinload(Generation.user))
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_last_generation(session: AsyncSession, telegram_id: int) -> Optional[Generation]:
    """Gets the very last generation for a user."""
    stmt = (
        select(Generation)
        .join(User)
        .where(User.telegram_id == telegram_id)
        .order_by(Generation.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

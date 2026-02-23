from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import ConversationHistory, User


async def save_to_memory(session: AsyncSession, user_id: int, request: str, response: str):
    """Saves a new request-response pair to the conversation history."""
    history_entry = ConversationHistory(
        user_id=user_id,
        request=request,
        response=response
    )
    session.add(history_entry)
    await session.commit()


async def get_recent_memory(session: AsyncSession, user_id: int, limit: int = 20) -> List[ConversationHistory]:
    """Retrieves the most recent conversation history for a user."""
    stmt = (
        select(ConversationHistory)
        .where(ConversationHistory.user_id == user_id)
        .order_by(ConversationHistory.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return result.scalars().all()

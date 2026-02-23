from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

from src.config import settings

class AuthMiddleware(BaseMiddleware):
    """
    Middleware to check if the user is in the allowed list.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # If ALLOWED_TELEGRAM_IDS is not set, allow all users.
        if not settings.allowed_telegram_ids:
            return await handler(event, data)

        # The user is not always available in the event data, so we need to check.
        user = data.get("event_from_user")
        if not user:
             return await handler(event, data)
        
        if user.id not in settings.allowed_telegram_ids:
            if isinstance(event, Message):
                await event.answer("🚫 Access Denied. You are not authorized to use this bot.")
            # Stop processing the update
            return

        return await handler(event, data)

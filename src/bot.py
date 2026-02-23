import asyncio
import logging
import pathlib
import pkgutil
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database.db import async_session, init_db
from src.handlers import common
from src.middlewares.auth import AuthMiddleware


async def main():
    """Main function to start the bot."""

    # Initialize database
    await init_db()

    # Initialize Bot and Dispatcher
    bot = Bot(token=settings.bot_token)
    redis = Redis(host=settings.redis_host, port=settings.redis_port)
    storage = RedisStorage(redis=redis)
    dp = Dispatcher(storage=storage)

    # Register middlewares
    dp.update.middleware(AuthMiddleware())

    # Custom middleware to pass the session to handlers
    @dp.update.middleware
    async def db_session_middleware(handler, event, data):
        async with async_session() as session:
            data['session'] = session
            return await handler(event, data)

    # Register base routers from handlers
    dp.include_router(common.router)

    # Auto-register routers from plugins
    plugins_path = pathlib.Path(__file__).parent / "plugins"
    for _, name, _ in pkgutil.iter_modules([str(plugins_path)]):
        if not name.startswith("_"):
            try:
                plugin_module = __import__(f"src.plugins.{name}", fromlist=["router"])
                if hasattr(plugin_module, "router"):
                    dp.include_router(plugin_module.router)
                    logging.info(f"Successfully registered plugin: {name}")
                else:
                    logging.warning(f"Plugin {name} does not have a 'router' attribute.")
            except ImportError as e:
                logging.error(f"Failed to import plugin {name}: {e}")

    # Start the bot
    try:
        if settings.bot_mode == "webhook":
            # You would need aiohttp and further setup for webhook
            logging.info("Webhook mode is selected, but not implemented in this basic setup.")
            logging.info("Falling back to polling.")
            await dp.start_polling(bot)
        else:
            logging.info("Starting bot in polling mode...")
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await redis.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")

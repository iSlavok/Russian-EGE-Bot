from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand
from dishka import AsyncContainer
from dishka.integrations.aiogram import setup_dishka
from loguru import logger
from redis.asyncio.client import Redis

from app.config import redis_settings, settings
from bot.handlers import category_router, main_router, task_router
from bot.middlewares import MessageManagerMiddleware, UserMiddleware


async def start_bot(app_container: AsyncContainer) -> None:
    bot = Bot(token=settings.BOT_TOKEN.get_secret_value(), default=DefaultBotProperties(parse_mode="HTML"))
    storage = RedisStorage(
        redis=Redis(
            host=redis_settings.HOST,
            port=redis_settings.PORT,
            username=redis_settings.USERNAME,
            password=redis_settings.PASSWORD.get_secret_value(),
            db=redis_settings.DB,
        ),
        key_builder=DefaultKeyBuilder(
            with_destiny=True,
            with_bot_id=True,
        ),
    )
    dp = Dispatcher(storage=storage)

    message_manager_middleware = MessageManagerMiddleware()
    user_middleware = UserMiddleware()

    dp.message.middleware(message_manager_middleware)
    dp.callback_query.middleware(message_manager_middleware)

    dp.message.middleware(user_middleware)
    dp.callback_query.middleware(user_middleware)

    dp.include_router(main_router)
    dp.include_router(category_router)
    dp.include_router(task_router)

    setup_dishka(container=app_container, router=dp, auto_inject=True)

    commands = [
        BotCommand(command="menu", description="Главное меню"),
    ]
    await bot.set_my_commands(commands)

    try:
        logger.info("Starting bot polling...")
        await dp.start_polling(bot)
    finally:
        await app_container.close()

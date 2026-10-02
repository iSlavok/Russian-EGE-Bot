import asyncio
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand
from dishka import AsyncContainer
from dishka.integrations.aiogram import setup_dishka
from loguru import logger
from redis.asyncio.client import Redis

from app.config import redis_settings, settings, shutdown_logging
from bot.handlers import category_router, main_router, profile_router, task_router
from bot.middlewares import (
    ErrorHandlerMiddleware,
    MessageManagerMiddleware,
    UserMiddleware,
    handle_unexpected_error,
)
from bot.utils import run_limiter_cleanup, setup_rate_limiter


async def start_bot(app_container: AsyncContainer) -> None:
    bot = Bot(token=settings.BOT_TOKEN.get_secret_value(), default=DefaultBotProperties(parse_mode="HTML"))
    rate_limiter = setup_rate_limiter(bot)
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

    error_middleware = ErrorHandlerMiddleware()
    message_manager_middleware = MessageManagerMiddleware()
    user_middleware = UserMiddleware()

    dp.message.middleware(error_middleware)
    dp.callback_query.middleware(error_middleware)

    dp.message.middleware(message_manager_middleware)
    dp.callback_query.middleware(message_manager_middleware)

    dp.message.middleware(user_middleware)
    dp.callback_query.middleware(user_middleware)

    dp.errors.register(handle_unexpected_error)

    dp.include_router(main_router)
    dp.include_router(profile_router)
    dp.include_router(category_router)
    dp.include_router(task_router)

    setup_dishka(container=app_container, router=dp, auto_inject=True)

    commands = [
        BotCommand(command="menu", description="Главное меню"),
    ]
    await bot.set_my_commands(commands)

    cleanup_task = asyncio.create_task(run_limiter_cleanup(rate_limiter))

    try:
        logger.info("Bot initialized, starting polling...")
        await dp.start_polling(bot)
    finally:
        logger.info("Shutting down bot...")
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task
        await app_container.close()
        logger.info("Bot stopped")
        await shutdown_logging()

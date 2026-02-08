from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.types import User as TelegramUser
from dishka.integrations.aiogram import CONTAINER_NAME

from app.services.user_service import UserService

if TYPE_CHECKING:
    from dishka import AsyncContainer


class UserMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        super().__init__()

    async def __call__(
            self,
            handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: dict[str, Any],
    ) -> dict[str, Any]:
        event_from_user: TelegramUser | None = data["event_from_user"]
        if event_from_user:
            container: AsyncContainer = data[CONTAINER_NAME]
            user_service = await container.get(UserService)

            data["user"] = await user_service.get_user_by_telegram(
                telegram_id=event_from_user.id,
                tg_username=event_from_user.username,
                full_name=event_from_user.full_name,
            )

        return await handler(event, data)

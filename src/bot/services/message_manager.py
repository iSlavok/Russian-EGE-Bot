import asyncio
from collections import defaultdict
from contextlib import suppress
from typing import Any, Self, cast

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

_user_locks = defaultdict(asyncio.Lock)


class MessageManager:
    def __init__(self, bot: Bot, chat_id: int, state: FSMContext, message: Message) -> None:
        self.bot = bot
        self.chat_id = chat_id
        self.state = state
        self.message = message
        self._lock = _user_locks[chat_id]

        self._bot_messages_key = "bot_messages"
        self._user_messages_key = "user_messages"

    @classmethod
    async def from_message(cls, bot: Bot, message: Message, state: FSMContext) -> Self:
        manager = cls(
            bot=bot,
            chat_id=message.chat.id,
            state=state,
            message=message,
        )
        await manager.add_user_message(message.message_id)
        return manager

    @classmethod
    async def from_callback(cls, bot: Bot, callback: CallbackQuery, state: FSMContext) -> Self:
        message = cast("Message", callback.message)
        manager = cls(
            bot=bot,
            chat_id=message.chat.id,
            state=state,
            message=message,
        )
        await manager.add_bot_message(message.message_id)
        return manager

    async def send_message(
            self,
            text: str,
            *, clear_previous: bool = True,
            keep_bot_last: int = 1,
            **kwargs: Any,  # noqa: ANN401
    ) -> Message:
        async with self._lock:
            data = await self._load_data()

            message = await self._send_message_no_lock(
                data=data,
                text=text,
                clear_previous=clear_previous,
                keep_bot_last=keep_bot_last,
                **kwargs,
            )

            await self._save_data(data)

        return message

    async def _send_message_no_lock(
            self,
            data: dict,
            text: str,
            *, clear_previous: bool = True,
            keep_bot_last: int = 1,
            **kwargs: Any,  # noqa: ANN401
    ) -> Message:
        message = await self.bot.send_message(chat_id=self.chat_id, text=text, **kwargs)
        self._add_bot_message(message.message_id, data)

        if clear_previous:
            await self._clear_messages(data, keep_bot_last=keep_bot_last)

        return message

    async def edit_message(
            self,
            text: str,
            message_number: int = 1,
            *, clear_previous: bool = True,
            keep_bot_last: int = 1,
            **kwargs: Any,  # noqa: ANN401
    ) -> Message | bool:
        async with self._lock:
            data = await self._load_data()

            bot_messages = self._get_bot_messages(data)
            if len(bot_messages) < message_number:
                message = await self._send_message_no_lock(
                    data=data,
                    text=text,
                    clear_previous=clear_previous,
                    keep_bot_last=keep_bot_last,
                    **kwargs,
                )
                await self._save_data(data)
                return message

            try:
                last_bot_msg_id = bot_messages[-message_number]

                result = await self.bot.edit_message_text(
                    text=text,
                    chat_id=self.chat_id,
                    message_id=last_bot_msg_id,
                    **kwargs,
                )

                await self._clear_messages(data, keep_bot_last=keep_bot_last)

            except TelegramBadRequest:
                result = await self._send_message_no_lock(
                    data=data,
                    text=text,
                    clear_previous=clear_previous,
                    keep_bot_last=keep_bot_last,
                    **kwargs,
                )

            await self._save_data(data)

        return result

    async def _load_data(self) -> dict:
        return await self.state.get_data()

    async def _save_data(self, data: dict) -> None:
        await self.state.update_data(data)

    async def add_bot_message(self, message_id: int) -> None:
        async with self._lock:
            data = await self._load_data()
            self._add_bot_message(message_id, data)
            await self._save_data(data)

    def _add_bot_message(self, message_id: int, data: dict) -> None:
        bot_messages = self._get_bot_messages(data)
        if message_id not in bot_messages:
            bot_messages.append(message_id)

    async def add_user_message(self, message_id: int) -> None:
        async with self._lock:
            data = await self._load_data()
            self._add_user_message(message_id, data)
            await self._save_data(data)

    def _add_user_message(self, message_id: int, data: dict) -> None:
        user_messages = self._get_user_messages(data)
        if message_id not in user_messages:
            user_messages.append(message_id)

    def _get_bot_messages(self, data: dict) -> list[int]:
        return data.setdefault(self._bot_messages_key, [])

    def _get_user_messages(self, data: dict) -> list[int]:
        return data.setdefault(self._user_messages_key, [])

    async def clear_messages(self, keep_bot_last: int = 0) -> None:
        async with self._lock:
            data = await self._load_data()
            await self._clear_messages(data, keep_bot_last=keep_bot_last)
            await self._save_data(data)

    async def _clear_messages(self, data: dict, keep_bot_last: int) -> None:
        bot_messages = self._get_bot_messages(data)
        while len(bot_messages) > keep_bot_last:
            message_id = bot_messages.pop(0)

            try:
                await self.bot.delete_message(self.chat_id, message_id)
            except TelegramBadRequest:
                with suppress(TelegramBadRequest):
                    await self.bot.edit_message_text(
                        chat_id=self.chat_id,
                        message_id=message_id,
                        text="[Сообщение устарело]",
                    )

        user_messages = self._get_user_messages(data)
        while user_messages:
            msg_id = user_messages.pop(0)
            with suppress(TelegramBadRequest):
                await self.bot.delete_message(self.chat_id, msg_id)

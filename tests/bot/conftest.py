from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from aiogram import Bot
from aiogram.types import Chat, Message


class FakeFSMContext:
    """Dict-backed replacement for FSMContext — no Redis needed."""

    def __init__(self, initial_data: dict | None = None):
        self._data: dict = initial_data or {}

    async def get_data(self) -> dict:
        return self._data.copy()

    async def update_data(self, data: dict | None = None, **kwargs) -> None:
        if data:
            self._data.update(data)
        self._data.update(kwargs)


def make_message(message_id: int = 1, chat_id: int = 123) -> Message:
    return Message(
        message_id=message_id,
        date=datetime.now(UTC),
        chat=Chat(id=chat_id, type="private"),
    )


@pytest.fixture
def mock_bot():
    bot = AsyncMock(spec=Bot)
    bot.send_message.return_value = make_message(message_id=100)
    bot.edit_message_text.return_value = True
    bot.delete_message.return_value = True
    return bot


@pytest.fixture
def fake_state():
    return FakeFSMContext()

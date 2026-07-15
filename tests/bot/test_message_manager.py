import pytest
from aiogram.exceptions import TelegramBadRequest

from bot.services.message_manager import MessageManager

from .conftest import FakeFSMContext, make_message


@pytest.fixture
def manager(mock_bot, fake_state):
    msg = make_message(message_id=1, chat_id=123)
    return MessageManager(bot=mock_bot, chat_id=123, state=fake_state, message=msg)


# ── from_message / from_callback ─────────────────────────────────────────────


class TestFactoryMethods:
    async def test_from_message_stores_user_message(self, mock_bot, fake_state):
        msg = make_message(message_id=42, chat_id=123)
        manager = await MessageManager.from_message(mock_bot, msg, fake_state)
        data = await fake_state.get_data()
        assert 42 in data["user_messages"]
        assert manager.chat_id == 123

    async def test_from_callback_stores_bot_message(self, mock_bot, fake_state):
        from unittest.mock import MagicMock

        from aiogram.types import CallbackQuery

        msg = make_message(message_id=55, chat_id=123)
        callback = MagicMock(spec=CallbackQuery)
        callback.message = msg

        manager = await MessageManager.from_callback(mock_bot, callback, fake_state)
        data = await fake_state.get_data()
        assert 55 in data["bot_messages"]
        assert manager.chat_id == 123


# ── send_message ─────────────────────────────────────────────────────────────


class TestSendMessage:
    async def test_send_message_calls_bot_and_records_id(self, manager, mock_bot, fake_state):
        result = await manager.send_message("hello", clear_previous=False)
        mock_bot.send_message.assert_called_once_with(chat_id=123, text="hello")
        data = await fake_state.get_data()
        assert 100 in data["bot_messages"]
        assert result.message_id == 100

    async def test_send_message_clears_previous_by_default(self, manager, mock_bot, fake_state):
        # Seed a bot message to be cleared
        await fake_state.update_data(bot_messages=[10], user_messages=[20])

        await manager.send_message("hi")

        mock_bot.delete_message.assert_any_call(123, 10)
        mock_bot.delete_message.assert_any_call(123, 20)

    async def test_send_message_no_clear_when_disabled(self, manager, mock_bot, fake_state):
        await fake_state.update_data(bot_messages=[10])

        await manager.send_message("hi", clear_previous=False)

        mock_bot.delete_message.assert_not_called()


# ── edit_message ─────────────────────────────────────────────────────────────


class TestEditMessage:
    async def test_edit_message_happy_path(self, manager, mock_bot, fake_state):
        await fake_state.update_data(bot_messages=[50])

        await manager.edit_message("updated")

        mock_bot.edit_message_text.assert_called_once_with(
            text="updated", chat_id=123, message_id=50,
        )

    async def test_edit_message_fallback_when_not_enough_messages(self, manager, mock_bot, fake_state):
        # No bot messages — message_number=1 but len(bot_messages)=0
        await manager.edit_message("fallback")

        mock_bot.send_message.assert_called_once_with(chat_id=123, text="fallback")
        mock_bot.edit_message_text.assert_not_called()

    async def test_edit_message_fallback_on_telegram_bad_request(self, manager, mock_bot, fake_state):
        await fake_state.update_data(bot_messages=[50])
        mock_bot.edit_message_text.side_effect = TelegramBadRequest(
            method=None, message="Bad Request: message is not modified",
        )

        await manager.edit_message("retry")

        mock_bot.send_message.assert_called_once_with(chat_id=123, text="retry")


# ── clear_messages ───────────────────────────────────────────────────────────


class TestClearMessages:
    async def test_clear_keeps_last_bot_message(self, manager, mock_bot, fake_state):
        await fake_state.update_data(bot_messages=[10, 20, 30])

        await manager.clear_messages(keep_bot_last=1)

        mock_bot.delete_message.assert_any_call(123, 10)
        mock_bot.delete_message.assert_any_call(123, 20)
        data = await fake_state.get_data()
        assert data["bot_messages"] == [30]

    async def test_clear_deletes_user_messages(self, manager, mock_bot, fake_state):
        await fake_state.update_data(bot_messages=[], user_messages=[5, 6])

        await manager.clear_messages()

        mock_bot.delete_message.assert_any_call(123, 5)
        mock_bot.delete_message.assert_any_call(123, 6)
        data = await fake_state.get_data()
        assert data["user_messages"] == []

    async def test_clear_fallback_edit_on_delete_failure(self, mock_bot, fake_state):
        mock_bot.delete_message.side_effect = TelegramBadRequest(
            method=None, message="Bad Request: message can't be deleted",
        )
        msg = make_message(message_id=1, chat_id=123)
        manager = MessageManager(bot=mock_bot, chat_id=123, state=fake_state, message=msg)
        await fake_state.update_data(bot_messages=[10])

        await manager.clear_messages(keep_bot_last=0)

        mock_bot.edit_message_text.assert_called_once_with(
            chat_id=123, message_id=10, text="[Сообщение устарело]",
        )


# ── _add_bot_message duplicate check ────────────────────────────────────────


class TestAddBotMessage:
    async def test_add_bot_message_no_duplicate(self, manager, mock_bot, fake_state):
        await manager.add_bot_message(100)
        await manager.add_bot_message(100)
        data = await fake_state.get_data()
        assert data["bot_messages"].count(100) == 1


class TestSendRich:
    async def test_send_rich_calls_native_and_tracks_id(self, manager, mock_bot, fake_state):
        mock_bot.send_rich_message.return_value = make_message(message_id=200, chat_id=123)
        message_id = await manager.send_rich("**hi**")
        assert message_id == 200
        mock_bot.send_rich_message.assert_awaited_once()
        kwargs = mock_bot.send_rich_message.call_args.kwargs
        assert kwargs["chat_id"] == 123
        assert kwargs["rich_message"].markdown == "**hi**"
        assert kwargs["rich_message"].skip_entity_detection is True
        data = await fake_state.get_data()
        assert 200 in data["bot_messages"]

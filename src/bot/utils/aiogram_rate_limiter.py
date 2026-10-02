"""
Rate limiting for aiogram bots via the official session middleware hook.

Telegram API limits:
- Global: ~30 requests/second across all chats
- Private chats: ~1 *new message*/second per chat (edits, deletes and reactions
  live in a far more permissive bucket)
- Groups/channels: ~20 messages/minute per chat

Все лимиты здесь — token bucket, а не фиксированный интервал. Телеграмовские
лимиты средние: 429 приходит за устойчивое превышение, а не за два сообщения
подряд. Бот же на одно действие юзера делает несколько вызовов в один чат
(удалить старое, отправить результат, отправить следующее задание), поэтому
фиксированный интервал добавлял бы по секунде к каждому нажатию. Ведро
пропускает такой всплеск сразу и начинает притормаживать только того, кто
превышает средний темп.

Two independent per-chat buckets are used, because throttling edits and deletes
at the send rate would make every UI interaction take seconds: `SEND_METHODS`
gets the strict per-chat rate, `RELAXED_METHODS` gets a multiple of it.

A shared flood gate makes a single `TelegramRetryAfter` pause every in-flight
request for the bot, instead of letting the rest keep hammering the API.
"""

import asyncio
from time import monotonic
from typing import Any

from aiogram import Bot
from aiogram.client.session.middlewares.base import (
    BaseRequestMiddleware,
    NextRequestMiddlewareType,
)
from aiogram.exceptions import TelegramRetryAfter
from aiogram.methods import Response, TelegramMethod
from aiogram.methods.base import TelegramType
from loguru import logger

from bot.utils.smart_limiter_cache import SmartLimiterCache
from bot.utils.token_bucket_limiter import TokenBucketLimiter

RETRY_AFTER_BUFFER = 0.5

SEND_METHODS = frozenset({
    "CopyMessage",
    "ForwardMessage",
    "SendAnimation",
    "SendAudio",
    "SendContact",
    "SendDice",
    "SendDocument",
    "SendLocation",
    "SendMediaGroup",
    "SendMessage",
    "SendPhoto",
    "SendPoll",
    "SendRichMessage",
    "SendSticker",
    "SendVenue",
    "SendVideo",
    "SendVideoNote",
    "SendVoice",
})

RELAXED_METHODS = frozenset({
    "DeleteMessage",
    "DeleteMessages",
    "EditMessageCaption",
    "EditMessageMedia",
    "EditMessageReplyMarkup",
    "EditMessageText",
    "PinChatMessage",
    "SetMessageReaction",
    "UnpinChatMessage",
})


class FloodGate:
    """Общая пауза для всех запросов бота после 429 от Telegram.

    Telegram даёт flood wait на бота целиком, поэтому ждать должны все задачи,
    а не только та, которая получила ошибку.
    """

    def __init__(self) -> None:
        self._until = 0.0

    def pause(self, seconds: float) -> None:
        self._until = max(self._until, monotonic() + seconds)

    async def wait(self) -> None:
        while (delay := self._until - monotonic()) > 0:  # noqa: ASYNC110
            await asyncio.sleep(delay)


class RateLimitMiddleware(BaseRequestMiddleware):
    """Пропускает запросы к Bot API через глобальное и два по-чатовых ведра.

    :param global_rate: запросов за global_period по всем чатам (лимит Telegram — 30/с).
    :param global_period: окно глобального лимита в секундах.
    :param global_burst: сколько запросов подряд пропустить после простоя. Пик ведра
        в скользящем окне — global_burst + global_rate, поэтому сумма держится
        не выше телеграмовских 30/с.
    :param private_chat_rate: новых сообщений за период в приватный чат.
    :param private_chat_period: окно по-чатового лимита для приватных чатов.
    :param private_chat_burst: запас сообщений на одно действие юзера в приватном чате.
    :param group_chat_rate: новых сообщений за период в группу/канал.
    :param group_chat_period: окно по-чатового лимита для групп.
    :param group_chat_burst: запас сообщений для группы.
    :param relaxed_multiplier: во сколько раз правка/удаление быстрее отправки.
    :param max_cache_size: сколько по-чатовых лимитеров держать (LRU).
    :param cache_ttl: через сколько секунд простоя лимитер чата выбрасывается.
    :param max_retries: сколько раз повторить запрос после TelegramRetryAfter.
    """

    def __init__(
        self,
        global_rate: int = 25,
        global_period: float = 1.0,
        global_burst: int = 5,
        private_chat_rate: int = 1,
        private_chat_period: float = 1.0,
        private_chat_burst: int = 5,
        group_chat_rate: int = 20,
        group_chat_period: float = 60.0,
        group_chat_burst: int = 20,
        relaxed_multiplier: int = 5,
        max_cache_size: int = 10_000,
        cache_ttl: int = 300,
        max_retries: int = 3,
    ) -> None:
        self._max_retries = max_retries
        self._flood_gate = FloodGate()
        self._global_limiter = TokenBucketLimiter(global_rate, global_period, global_burst)
        self._send_limiters = SmartLimiterCache(
            maxsize=max_cache_size,
            ttl_seconds=cache_ttl,
            private_rate=private_chat_rate,
            private_period=private_chat_period,
            private_burst=private_chat_burst,
            group_rate=group_chat_rate,
            group_period=group_chat_period,
            group_burst=group_chat_burst,
        )
        self._relaxed_limiters = SmartLimiterCache(
            maxsize=max_cache_size,
            ttl_seconds=cache_ttl,
            private_rate=private_chat_rate * relaxed_multiplier,
            private_period=private_chat_period,
            private_burst=private_chat_burst * relaxed_multiplier,
            group_rate=group_chat_rate * relaxed_multiplier,
            group_period=group_chat_period,
            group_burst=group_chat_burst * relaxed_multiplier,
        )

    def cleanup_expired(self) -> int:
        """Выбрасывает лимитеры чатов, не использованные дольше cache_ttl."""
        return self._send_limiters.cleanup_expired() + self._relaxed_limiters.cleanup_expired()

    def _chat_limiter(self, method_name: str, chat_id: int | None) -> TokenBucketLimiter | None:
        if chat_id is None:
            return None
        if method_name in SEND_METHODS:
            return self._send_limiters.get(chat_id)
        if method_name in RELAXED_METHODS:
            return self._relaxed_limiters.get(chat_id)
        return None

    @staticmethod
    def _chat_id(method: TelegramMethod[TelegramType]) -> int | None:
        chat_id: Any = getattr(method, "chat_id", None)
        if isinstance(chat_id, int):
            return chat_id
        if isinstance(chat_id, str) and chat_id.lstrip("-").isdigit():
            return int(chat_id)
        return None

    async def __call__(
        self,
        make_request: NextRequestMiddlewareType[TelegramType],
        bot: Bot,
        method: TelegramMethod[TelegramType],
    ) -> Response[TelegramType]:
        method_name = type(method).__name__
        chat_id = self._chat_id(method)

        for attempt in range(1, self._max_retries + 1):
            try:
                await self._flood_gate.wait()
                async with self._global_limiter:
                    chat_limiter = self._chat_limiter(method_name, chat_id)
                    if chat_limiter is None:
                        return await make_request(bot, method)
                    async with chat_limiter:
                        return await make_request(bot, method)
            except TelegramRetryAfter as exc:
                self._flood_gate.pause(exc.retry_after + RETRY_AFTER_BUFFER)
                if attempt == self._max_retries:
                    logger.warning(
                        "Flood limit: giving up on {} (chat_id={}) after {} attempts",
                        method_name,
                        chat_id,
                        self._max_retries,
                    )
                    raise
                logger.warning(
                    "Flood limit on {} (chat_id={}): pausing {}s, attempt {}/{}",
                    method_name,
                    chat_id,
                    exc.retry_after,
                    attempt,
                    self._max_retries,
                )

        msg = "Unreachable: retry loop always returns or raises"
        raise RuntimeError(msg)


def setup_rate_limiter(bot: Bot, **kwargs: Any) -> RateLimitMiddleware:  # noqa: ANN401
    """Регистрирует RateLimitMiddleware в сессии бота.

    Идемпотентна: повторный вызов для того же бота вернёт уже установленную
    middleware, а не навесит вторую.

    :param bot: экземпляр Bot
    :param kwargs: параметры RateLimitMiddleware
    :return: установленная middleware (у неё можно звать cleanup_expired)
    """
    for existing in bot.session.middleware._middlewares:  # noqa: SLF001
        if isinstance(existing, RateLimitMiddleware):
            logger.warning("Rate limiter already installed for this bot, skipping")
            return existing

    middleware = RateLimitMiddleware(**kwargs)
    bot.session.middleware(middleware)
    logger.info("Rate limiter installed: {}", middleware)
    return middleware


async def run_limiter_cleanup(middleware: RateLimitMiddleware, interval: int = 300) -> None:
    """Фоновая задача: периодически чистит просроченные по-чатовые лимитеры.

    Работает до отмены. Отмену пробрасывает наружу, чтобы задачу можно было
    корректно дождаться при остановке бота.
    """
    while True:
        await asyncio.sleep(interval)
        try:
            middleware.cleanup_expired()
        except Exception:
            logger.exception("Rate limiter cleanup failed")

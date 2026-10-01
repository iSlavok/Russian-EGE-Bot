import asyncio
import inspect
from time import monotonic
from typing import cast

import pytest
from aiogram import Bot
from aiogram import methods as aiogram_methods
from aiogram.exceptions import TelegramRetryAfter
from aiogram.methods import AnswerCallbackQuery, DeleteMessage, SendMessage
from aiogram.methods.base import TelegramMethod

from bot.utils.aiogram_rate_limiter import (
    RELAXED_METHODS,
    SEND_METHODS,
    FloodGate,
    RateLimitMiddleware,
)
from bot.utils.smart_limiter_cache import SmartLimiterCache
from bot.utils.strict_rate_limiter import StrictRateLimiter

FAKE_BOT = cast("Bot", object())


def send_message(chat_id: int = 111) -> SendMessage:
    return SendMessage(chat_id=chat_id, text="hi")


def delete_message(chat_id: int = 111) -> DeleteMessage:
    return DeleteMessage(chat_id=chat_id, message_id=1)


class TestMethodSets:
    def test_sets_do_not_overlap(self):
        assert not SEND_METHODS & RELAXED_METHODS

    @pytest.mark.parametrize("name", sorted(SEND_METHODS | RELAXED_METHODS))
    def test_every_name_is_a_real_method_with_chat_id(self, name: str):
        """Опечатка в имени молча отключила бы лимит для этого метода."""
        method = getattr(aiogram_methods, name, None)
        assert inspect.isclass(method), f"{name} is not an aiogram method"
        assert issubclass(method, TelegramMethod)
        assert "chat_id" in method.model_fields

    def test_send_rich_message_is_limited(self):
        """Основной способ отправки в этом боте — send_rich_message."""
        assert "SendRichMessage" in SEND_METHODS

    def test_streaming_drafts_are_not_limited(self):
        for name in ("SendMessageDraft", "SendRichMessageDraft"):
            assert name not in SEND_METHODS | RELAXED_METHODS


class TestStrictRateLimiter:
    @pytest.mark.parametrize(("rate", "period"), [(0, 1.0), (-1, 1.0), (1, 0.0), (1, -1.0)])
    def test_rejects_non_positive_args(self, rate: int, period: float):
        with pytest.raises(ValueError, match="must be positive"):
            StrictRateLimiter(rate, period)

    async def test_first_acquire_is_immediate(self):
        limiter = StrictRateLimiter(rate=1, period=10.0)
        started = monotonic()
        await limiter.acquire()
        assert monotonic() - started < 0.05

    async def test_spaces_out_sequential_acquires(self):
        limiter = StrictRateLimiter(rate=20, period=1.0)  # 50ms apart
        started = monotonic()
        for _ in range(3):
            await limiter.acquire()
        assert monotonic() - started >= 0.1

    async def test_spaces_out_concurrent_acquires(self):
        limiter = StrictRateLimiter(rate=20, period=1.0)
        started = monotonic()
        await asyncio.gather(*(limiter.acquire() for _ in range(4)))
        assert monotonic() - started >= 0.15

    async def test_works_as_context_manager(self):
        limiter = StrictRateLimiter(rate=20, period=1.0)
        started = monotonic()
        async with limiter:
            pass
        async with limiter:
            pass
        assert monotonic() - started >= 0.05


class TestSmartLimiterCache:
    def test_returns_same_limiter_for_same_chat(self):
        cache = SmartLimiterCache()
        assert cache.get(5) is cache.get(5)

    def test_private_and_group_get_different_rates(self):
        cache = SmartLimiterCache(private_rate=1, private_period=1.0, group_rate=20, group_period=60.0)
        assert cache.get(5).min_interval == pytest.approx(1.0)
        assert cache.get(-5).min_interval == pytest.approx(3.0)

    def test_lru_evicts_oldest(self):
        cache = SmartLimiterCache(maxsize=2)
        first = cache.get(1)
        cache.get(2)
        cache.get(3)
        assert 1 not in cache.cache
        assert cache.get(1) is not first

    def test_touching_entry_protects_it_from_eviction(self):
        cache = SmartLimiterCache(maxsize=2)
        first = cache.get(1)
        cache.get(2)
        assert cache.get(1) is first  # refreshes LRU position
        cache.get(3)
        assert 1 in cache.cache
        assert 2 not in cache.cache

    def test_cleanup_removes_only_expired(self):
        cache = SmartLimiterCache(ttl_seconds=300)
        stale = cache.get(1)
        fresh = cache.get(2)
        cache.cache[1] = (stale, monotonic() - 1000)

        assert cache.cleanup_expired() == 1
        assert 1 not in cache.cache
        assert cache.get(2) is fresh


class TestFloodGate:
    async def test_passes_through_when_not_paused(self):
        gate = FloodGate()
        started = monotonic()
        await gate.wait()
        assert monotonic() - started < 0.05

    async def test_blocks_until_deadline(self):
        gate = FloodGate()
        gate.pause(0.15)
        started = monotonic()
        await gate.wait()
        assert monotonic() - started >= 0.1

    async def test_pause_never_shortens_existing_deadline(self):
        gate = FloodGate()
        gate.pause(0.2)
        gate.pause(0.01)
        started = monotonic()
        await gate.wait()
        assert monotonic() - started >= 0.15

    async def test_extending_deadline_while_waiting_is_respected(self):
        gate = FloodGate()
        gate.pause(0.05)

        async def extend() -> None:
            await asyncio.sleep(0.02)
            gate.pause(0.2)

        started = monotonic()
        await asyncio.gather(gate.wait(), extend())
        assert monotonic() - started >= 0.2


class TestRateLimitMiddlewareBuckets:
    def test_send_and_relaxed_use_separate_limiters(self):
        mw = RateLimitMiddleware()
        send = mw._chat_limiter("SendMessage", 111)  # noqa: SLF001
        relaxed = mw._chat_limiter("DeleteMessage", 111)  # noqa: SLF001
        assert send is not None
        assert relaxed is not None
        assert send is not relaxed

    def test_relaxed_bucket_is_faster(self):
        mw = RateLimitMiddleware(private_chat_rate=1, private_chat_period=1.0, relaxed_multiplier=5)
        send = mw._chat_limiter("SendMessage", 111)  # noqa: SLF001
        relaxed = mw._chat_limiter("DeleteMessage", 111)  # noqa: SLF001
        assert send is not None
        assert relaxed is not None
        assert relaxed.min_interval == pytest.approx(send.min_interval / 5)

    def test_unknown_method_gets_no_chat_limiter(self):
        mw = RateLimitMiddleware()
        assert mw._chat_limiter("GetChat", 111) is None  # noqa: SLF001

    def test_no_chat_id_gets_no_chat_limiter(self):
        mw = RateLimitMiddleware()
        assert mw._chat_limiter("SendMessage", None) is None  # noqa: SLF001

    @pytest.mark.parametrize(
        ("method", "expected"),
        [
            (send_message(42), 42),
            (send_message(-100), -100),
            (AnswerCallbackQuery(callback_query_id="x"), None),
        ],
    )
    def test_chat_id_extraction(self, method: TelegramMethod, expected: int | None):
        assert RateLimitMiddleware._chat_id(method) == expected  # noqa: SLF001

    def test_string_chat_id_is_parsed(self):
        method = SendMessage(chat_id="-1001234", text="hi")
        assert RateLimitMiddleware._chat_id(method) == -1001234  # noqa: SLF001

    def test_username_chat_id_is_ignored(self):
        method = SendMessage(chat_id="@channel", text="hi")
        assert RateLimitMiddleware._chat_id(method) is None  # noqa: SLF001

    def test_cleanup_expired_covers_both_buckets(self):
        mw = RateLimitMiddleware()
        send = mw._chat_limiter("SendMessage", 111)  # noqa: SLF001
        relaxed = mw._chat_limiter("DeleteMessage", 111)  # noqa: SLF001
        assert send is not None
        assert relaxed is not None
        mw._send_limiters.cache[111] = (send, monotonic() - 1000)  # noqa: SLF001
        mw._relaxed_limiters.cache[111] = (relaxed, monotonic() - 1000)  # noqa: SLF001
        assert mw.cleanup_expired() == 2


class TestRateLimitMiddlewareCall:
    async def test_passes_result_through(self):
        mw = RateLimitMiddleware()

        async def make_request(bot, method):  # noqa: ANN001, ANN202, ARG001
            return "result"

        assert await mw(make_request, FAKE_BOT, send_message()) == "result"

    async def test_edits_are_not_paced_at_send_rate(self):
        """Удаления/правки не должны тормозить UI на 1/с — иначе каждое действие юзера 3 секунды."""
        mw = RateLimitMiddleware(private_chat_rate=1, private_chat_period=1.0, relaxed_multiplier=50)

        async def make_request(bot, method):  # noqa: ANN001, ANN202, ARG001
            return True

        started = monotonic()
        await asyncio.gather(*(mw(make_request, FAKE_BOT, delete_message()) for _ in range(3)))
        assert monotonic() - started < 0.5

    async def test_sends_to_same_chat_are_paced(self):
        mw = RateLimitMiddleware(private_chat_rate=10, private_chat_period=1.0)

        async def make_request(bot, method):  # noqa: ANN001, ANN202, ARG001
            return True

        started = monotonic()
        await asyncio.gather(*(mw(make_request, FAKE_BOT, send_message()) for _ in range(3)))
        assert monotonic() - started >= 0.2

    async def test_retries_after_flood_error(self):
        mw = RateLimitMiddleware(max_retries=3)
        calls = 0

        async def make_request(bot, method):  # noqa: ANN001, ANN202, ARG001
            nonlocal calls
            calls += 1
            if calls == 1:
                raise TelegramRetryAfter(method=method, message="flood", retry_after=0)
            return "ok"

        assert await mw(make_request, FAKE_BOT, send_message()) == "ok"
        assert calls == 2

    async def test_raises_after_max_retries(self):
        mw = RateLimitMiddleware(max_retries=2)
        calls = 0

        async def make_request(bot, method):  # noqa: ANN001, ANN202, ARG001
            nonlocal calls
            calls += 1
            raise TelegramRetryAfter(method=method, message="flood", retry_after=0)

        with pytest.raises(TelegramRetryAfter):
            await mw(make_request, FAKE_BOT, send_message())
        assert calls == 2

    async def test_flood_error_pauses_other_requests(self):
        """429 на одном запросе должен притормозить всех, а не только пострадавшего."""
        mw = RateLimitMiddleware(max_retries=1)

        async def flooded(bot, method):  # noqa: ANN001, ANN202, ARG001
            raise TelegramRetryAfter(method=method, message="flood", retry_after=1)

        with pytest.raises(TelegramRetryAfter):
            await mw(flooded, FAKE_BOT, send_message(chat_id=1))

        async def ok(bot, method):  # noqa: ANN001, ANN202, ARG001
            return "ok"

        started = monotonic()
        task = asyncio.create_task(mw(ok, FAKE_BOT, send_message(chat_id=2)))
        await asyncio.sleep(0.1)
        assert not task.done(), "другой чат должен ждать общую flood-паузу"
        task.cancel()
        assert monotonic() - started >= 0.1

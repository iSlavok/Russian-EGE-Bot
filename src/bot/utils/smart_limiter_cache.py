"""
LRU cache with TTL for managing per-chat rate limiters.

This module provides SmartLimiterCache, which manages a pool of rate limiters
for different Telegram chats. It automatically creates appropriate limiters based
on chat type (private vs group) and handles cache eviction via LRU and TTL policies.
"""

from collections import OrderedDict
from time import monotonic

from loguru import logger

from bot.utils.token_bucket_limiter import TokenBucketLimiter


class SmartLimiterCache:
    """
    LRU cache with TTL for per-chat rate limiters.

    Manages a pool of TokenBucketLimiter instances, one per chat. Automatically
    creates limiters with appropriate rates based on chat type (private vs group).

    The cache uses two eviction policies:
    - LRU (Least Recently Used): Evicts oldest entries when maxsize is reached
    - TTL (Time To Live): Removes entries that haven't been used for ttl_seconds

    Chat type detection:
    - Positive chat_id: Private chat (stricter rate limits)
    - Negative chat_id: Group/channel (more relaxed rate limits)

    Example::

        cache = SmartLimiterCache(
            maxsize=1000,
            private_rate=1,
            private_period=1.0,
            private_burst=5,
            group_rate=20,
            group_period=60.0,
        )

        limiter = cache.get(12345)
        async with limiter:
            await send_message()

    :param maxsize: Maximum number of limiters to keep in cache.
                   When exceeded, oldest entries are evicted (LRU).
    :param ttl_seconds: Time in seconds after which unused limiter expires.
                       Entries not accessed within this time are removed.
    :param private_rate: Maximum requests per period for private chats.
    :param private_period: Time period in seconds for private chat rate limit.
    :param private_burst: Сколько запросов подряд можно сделать в приватный чат
                         после простоя; по умолчанию равно private_rate.
    :param group_rate: Maximum requests per period for groups/channels.
    :param group_period: Time period in seconds for group rate limit.
    :param group_burst: То же для групп; по умолчанию равно group_rate.
    """

    def __init__(
        self,
        maxsize: int = 1000,
        ttl_seconds: int = 300,
        private_rate: int = 1,
        private_period: float = 1.0,
        private_burst: int | None = None,
        group_rate: int = 20,
        group_period: float = 60.0,
        group_burst: int | None = None,
    ) -> None:
        """
        Initialize the limiter cache.

        :param maxsize: Maximum number of limiters to keep in cache (default: 1000)
        :param ttl_seconds: Time in seconds after which unused limiter expires (default: 300)
        :param private_rate: Requests per period for private chats (default: 1/sec)
        :param private_period: Period for private chats in seconds (default: 1)
        :param private_burst: Burst capacity for private chats (default: private_rate)
        :param group_rate: Requests per period for groups (default: 20/min)
        :param group_period: Period for groups in seconds (default: 60)
        :param group_burst: Burst capacity for groups (default: group_rate)
        """
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self.private_rate = private_rate
        self.private_period = private_period
        self.private_burst = private_burst
        self.group_rate = group_rate
        self.group_period = group_period
        self.group_burst = group_burst
        self.cache: OrderedDict[int, tuple[TokenBucketLimiter, float]] = OrderedDict()

    def _create_limiter(self, chat_id: int) -> TokenBucketLimiter:
        """
        Create appropriate limiter based on chat type.

        Detects chat type by chat_id sign:
        - Positive ID: Private chat -> uses private_rate/private_period/private_burst
        - Negative ID: Group/channel -> uses group_rate/group_period/group_burst

        :param chat_id: Telegram chat ID (positive for private, negative for groups)
        :return: Configured TokenBucketLimiter instance for the chat type
        """
        if chat_id > 0:
            return TokenBucketLimiter(self.private_rate, self.private_period, self.private_burst)
        return TokenBucketLimiter(self.group_rate, self.group_period, self.group_burst)

    def get(self, chat_id: int) -> TokenBucketLimiter:
        """
        Get or create a rate limiter for the specified chat.

        If limiter exists in cache:
        - Updates its last-used timestamp
        - Moves it to the end of LRU queue
        - Returns existing limiter

        If limiter doesn't exist:
        - Creates new limiter based on chat type
        - Adds it to cache
        - Evicts oldest entries if maxsize exceeded

        :param chat_id: Telegram chat ID (positive for private, negative for groups)
        :return: TokenBucketLimiter instance for the chat
        """
        now = monotonic()

        if chat_id in self.cache:
            limiter, _ = self.cache[chat_id]
            self.cache.move_to_end(chat_id)
            self.cache[chat_id] = (limiter, now)
            return limiter

        limiter = self._create_limiter(chat_id)
        self.cache[chat_id] = (limiter, now)

        while len(self.cache) > self.maxsize:
            oldest_chat_id, _ = self.cache.popitem(last=False)
            logger.debug(f"LRU: removed limiter for chat {oldest_chat_id}")

        return limiter

    def cleanup_expired(self) -> int:
        """
        Remove expired limiters based on TTL.

        Scans all cache entries and removes those that haven't been accessed
        within ttl_seconds. This is typically called periodically by a
        background task.

        :return: Number of expired limiters removed
        """
        now = monotonic()
        expired = [
            chat_id
            for chat_id, (_, last_used) in self.cache.items()
            if now - last_used > self.ttl_seconds
        ]

        for chat_id in expired:
            del self.cache[chat_id]

        if expired:
            logger.info(f"TTL cleanup: removed {len(expired)} expired chat limiters")

        return len(expired)

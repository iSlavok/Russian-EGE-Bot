"""
Token bucket rate limiter.

Держит средний темп rate/period, но разрешает всплеск до burst запросов
подряд без ожидания. Для интерактивного бота это важно: одно действие юзера
превращается в несколько вызовов Bot API в один и тот же чат, и платить
за них полным интервалом — значит добавлять секунды к каждому нажатию.
"""

import asyncio
from time import monotonic
from types import TracebackType
from typing import Self


class TokenBucketLimiter:
    """
    Лимитер с ведром токенов.

    Ведро наполняется со скоростью rate/period токенов в секунду и вмещает
    не больше burst. Каждый запрос забирает один токен; если токенов нет,
    задача спит ровно до появления следующего.

    Средний темп на длинном горизонте равен rate за period, но первые burst
    запросов после простоя проходят мгновенно.

    Ожидание идёт под общим локом, поэтому задачи получают токены в порядке
    очереди (FIFO) и никто не остаётся без слота.

    Пример::

        limiter = TokenBucketLimiter(rate=1, period=1.0, burst=5)
        async with limiter:
            await send_message()

    :param rate: сколько запросов разрешено за period
    :param period: окно лимита в секундах
    :param burst: ёмкость ведра; по умолчанию равна rate
    :raises ValueError: если rate, period или burst не положительны
    """

    def __init__(self, rate: int, period: float = 1.0, burst: int | None = None) -> None:
        if rate <= 0:
            msg = "Rate must be positive"
            raise ValueError(msg)
        if period <= 0:
            msg = "Period must be positive"
            raise ValueError(msg)
        if burst is not None and burst <= 0:
            msg = "Burst must be positive"
            raise ValueError(msg)

        self.rate = rate
        self.period = period
        self.burst = float(burst if burst is not None else rate)
        self.refill_rate = rate / period
        self._tokens = self.burst
        self._updated = monotonic()
        self._lock = asyncio.Lock()

    @property
    def tokens(self) -> float:
        """Сколько токенов в ведре с учётом наполнения с последнего запроса."""
        return min(self.burst, self._tokens + (monotonic() - self._updated) * self.refill_rate)

    async def acquire(self) -> None:
        """
        Забирает один токен, при необходимости дождавшись его появления.

        Пока в ведре есть токены, возвращает управление сразу. Когда ведро
        пусто, спит до момента, когда накопится ровно один токен.

        :return: None
        """
        async with self._lock:
            while True:
                now = monotonic()
                self._tokens = min(self.burst, self._tokens + (now - self._updated) * self.refill_rate)
                self._updated = now

                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return

                await asyncio.sleep((1.0 - self._tokens) / self.refill_rate)

    async def __aenter__(self) -> Self:
        """Забирает токен на входе в блок."""
        await self.acquire()
        return self

    async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: TracebackType | None,
    ) -> None:
        """Ничего не освобождает: токен возвращается только наполнением ведра."""

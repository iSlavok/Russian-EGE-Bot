from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserStat
from app.repositories import BaseRepository


class UserStatRepository(BaseRepository[UserStat]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserStat)

    async def get_or_create(self, user_id: int) -> UserStat:
        stmt = select(UserStat).where(UserStat.user_id == user_id)
        result = await self.session.execute(stmt)
        stat = result.scalars().first()
        if stat is None:
            stat = UserStat(user_id=user_id)
            self.session.add(stat)
            await self.session.flush([stat])
        return stat

    async def increment_answer(self, user_id: int, *, is_correct: bool, answer_date: date) -> None:
        stat = await self.get_or_create(user_id)

        stat.total_answered += 1

        if is_correct:
            stat.total_correct += 1
            stat.current_streak += 1
            stat.max_streak = max(stat.max_streak, stat.current_streak)
        else:
            stat.current_streak = 0

        prev_date = stat.last_answer_date
        if prev_date is None:
            stat.current_daily_streak = 1
        elif answer_date == prev_date:
            pass
        elif (answer_date - prev_date).days == 1:
            stat.current_daily_streak += 1
        else:
            stat.current_daily_streak = 1

        stat.max_daily_streak = max(stat.max_daily_streak, stat.current_daily_streak)

        stat.last_answer_date = answer_date

        await self.session.flush([stat])

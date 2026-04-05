from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserCategoryStat
from app.repositories import BaseRepository


class UserCategoryStatRepository(BaseRepository[UserCategoryStat]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserCategoryStat)

    async def get_all_by_user(self, user_id: int) -> Sequence[UserCategoryStat]:
        stmt = select(UserCategoryStat).where(UserCategoryStat.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def increment_answer(
        self, user_id: int, category_id: int, *, is_correct: bool, is_new_exercise: bool,
    ) -> None:
        stmt = select(UserCategoryStat).where(
            UserCategoryStat.user_id == user_id,
            UserCategoryStat.category_id == category_id,
        )
        result = await self.session.execute(stmt)
        stat = result.scalars().first()

        if stat is None:
            stat = UserCategoryStat(
                user_id=user_id,
                category_id=category_id,
                total_answered=1,
                total_correct=1 if is_correct else 0,
                distinct_answered=1 if is_new_exercise else 0,
            )
            self.session.add(stat)
        else:
            stat.total_answered += 1
            if is_correct:
                stat.total_correct += 1
            if is_new_exercise:
                stat.distinct_answered += 1

        await self.session.flush([stat])

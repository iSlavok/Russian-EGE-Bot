from collections.abc import Iterable, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Exercise
from app.repositories import BaseRepository


class ExerciseRepository(BaseRepository[Exercise]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Exercise)

    async def get_random_exercise(self) -> Exercise | None:
        statement = (
            select(Exercise)
            .order_by(func.random())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_exercise_by_categories(self, category_ids: Iterable[int]) -> Exercise | None:
        statement = (
            select(Exercise)
            .where(Exercise.category_id.in_(category_ids))
            .order_by(func.random())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_random(self, category_id: int, limit: int) -> Sequence[Exercise]:
        statement = (
            select(Exercise)
            .where(Exercise.category_id == category_id)
            .order_by(func.random())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

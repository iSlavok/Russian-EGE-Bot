from collections.abc import Iterable, Sequence

from sqlalchemy import String, func, select
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

    async def get_random_with_content_filter(
        self, category_id: int, content_field: str, limit: int,
    ) -> Sequence[Exercise]:
        """Получает случайные упражнения, где content->>content_field IS NOT NULL."""
        statement = (
            select(Exercise)
            .where(
                Exercise.category_id == category_id,
                Exercise.content[content_field].as_string().isnot(None),
            )
            .order_by(func.random())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_random_distinct_group(
        self,
        category_id: int,
        limit: int,
        require_one_with_content_field: str | None = None,
    ) -> Sequence[Exercise]:
        """Получает случайные упражнения с уникальными group_id.

        NULL group_id считаются уникальными (каждый NULL — отдельная группа).
        Если require_one_with_content_field задан, гарантирует что хотя бы одно
        упражнение имеет это поле в content не null.
        """
        distinct_group = func.coalesce(
            Exercise.group_id.cast(String),
            func.gen_random_uuid().cast(String),
        )

        base_query = (
            select(Exercise)
            .where(Exercise.category_id == category_id)
            .distinct(distinct_group)
            .order_by(distinct_group, func.random())
        )

        if require_one_with_content_field is None:
            statement = base_query.limit(limit)
            result = await self.session.execute(statement)
            return result.scalars().all()

        required_query = (
            select(Exercise)
            .where(
                Exercise.category_id == category_id,
                Exercise.content[require_one_with_content_field].as_string().isnot(None),
            )
            .order_by(func.random())
            .limit(1)
        )
        required_result = await self.session.execute(required_query)
        required_exercise = required_result.scalar_one_or_none()
        if required_exercise is None:
            return []

        exclude_groups = []
        if required_exercise.group_id is not None:
            exclude_groups.append(required_exercise.group_id)

        rest_query = (
            select(Exercise)
            .where(
                Exercise.category_id == category_id,
                Exercise.id != required_exercise.id,
            )
            .distinct(distinct_group)
            .order_by(distinct_group, func.random())
            .limit(limit - 1)
        )

        if exclude_groups:
            rest_query = rest_query.where(
                (Exercise.group_id.is_(None)) | (~Exercise.group_id.in_(exclude_groups)),
            )

        rest_result = await self.session.execute(rest_query)
        rest_exercises = list(rest_result.scalars().all())

        return [required_exercise, *rest_exercises]

    async def get_random_with_distinct_answer(
        self, category_id: int, exclude_answer: str, limit: int,
    ) -> Sequence[Exercise]:
        """Получает случайные упражнения с уникальными значениями answer, исключая указанное."""
        statement = (
            select(Exercise)
            .where(Exercise.category_id == category_id, Exercise.answer != exclude_answer)
            .distinct(Exercise.answer)
            .order_by(Exercise.answer, func.random())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_random_by_answer(
        self, category_id: int, answer: str, limit: int,
    ) -> Sequence[Exercise]:
        """Получает случайные упражнения с конкретным значением answer."""
        statement = (
            select(Exercise)
            .where(Exercise.category_id == category_id, Exercise.answer == answer)
            .order_by(func.random())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

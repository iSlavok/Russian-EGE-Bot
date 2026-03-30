from collections.abc import Iterable, Sequence

from sqlalchemy import String, func, select, text
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

    async def get_random_excluding_answer(
        self, category_id: int, exclude_answer: str, limit: int,
    ) -> Sequence[Exercise]:
        """Получает случайные упражнения где answer != exclude_answer."""
        statement = (
            select(Exercise)
            .where(Exercise.category_id == category_id, Exercise.answer != exclude_answer)
            .order_by(func.random())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

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

    async def get_random_by_content_value(
        self, category_id: int, content_field: str, content_value: str, limit: int,
    ) -> Sequence[Exercise]:
        """Получает случайные упражнения, где content->>content_field == content_value."""
        statement = (
            select(Exercise)
            .where(
                Exercise.category_id == category_id,
                Exercise.content[content_field].as_string() == content_value,
            )
            .order_by(func.random())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_random_by_answer_and_content_value(
        self,
        category_id: int,
        answer: str,
        content_field: str,
        content_value: str,
        limit: int,
    ) -> Sequence[Exercise]:
        """Получает случайные упражнения с заданным answer и content->>content_field == content_value."""
        statement = (
            select(Exercise)
            .where(
                Exercise.category_id == category_id,
                Exercise.answer == answer,
                Exercise.content[content_field].as_string() == content_value,
            )
            .order_by(func.random())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_exam_22_exercises(self, category_id: int) -> Sequence[Exercise]:
        """Возвращает 5 совместимых упражнений для exam-режима задания 22.

        Использует рекурсивный CTE, который гарантирует:
        - ответы (found_devices) 5 предложений взаимно не пересекаются с present-устройствами других
        - other_devices никогда не попадут в варианты ответа
        - суммарное число distinct present-устройств <= 19, то есть хватит 4 дистракторов из 23
        """
        sql = text("""
            WITH RECURSIVE base_data AS (
                SELECT
                    id,
                    string_to_array(answer, ';') AS a_arr,
                    (string_to_array(answer, ';') ||
                     COALESCE(ARRAY(SELECT jsonb_array_elements_text(content->'other_devices')), '{}')) AS p_arr
                FROM exercises
                WHERE category_id = :category_id AND is_active = true
            ),
            exam_path AS (
                SELECT * FROM (
                    SELECT
                        ARRAY[id] AS ids,
                        a_arr AS c_a,
                        p_arr AS c_p,
                        1 AS depth
                    FROM base_data
                    ORDER BY random()
                    LIMIT 20
                ) AS initial_step
                UNION ALL
                SELECT
                    ep.ids || bd.id,
                    ep.c_a || bd.a_arr,
                    ep.c_p || bd.p_arr,
                    ep.depth + 1
                FROM exam_path ep
                CROSS JOIN LATERAL (
                    SELECT b.id, b.a_arr, b.p_arr
                    FROM base_data b
                    WHERE NOT (b.id = ANY(ep.ids))
                      AND NOT (b.a_arr && ep.c_p)
                      AND NOT (b.p_arr && ep.c_a)
                    ORDER BY random()
                    LIMIT 1
                ) bd
                WHERE ep.depth < 5
            )
            SELECT e.*
            FROM (
                SELECT ids FROM exam_path
                WHERE depth = 5
                  AND (SELECT count(DISTINCT x) FROM unnest(c_p) AS x) <= 19
                LIMIT 1
            ) chosen
            JOIN exercises e ON e.id = ANY(chosen.ids)
        """)
        stmt = select(Exercise).from_statement(sql.bindparams(category_id=category_id))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_random_same_answer_groups(
        self,
        category_id: int,
        group_size: int,
        num_groups: int,
        exclude_ids: list[int] | None = None,
    ) -> Sequence[Exercise]:
        """Получает num_groups групп по group_size упражнений с одинаковым answer в каждой.

        Каждая группа — случайный answer, в котором достаточно упражнений.
        Возвращает плоский список; группировка по answer на стороне вызывающего.
        Один SQL-запрос (CTE + window function).
        """
        base_filter = [Exercise.category_id == category_id]
        if exclude_ids:
            base_filter.append(Exercise.id.notin_(exclude_ids))

        eligible_sq = (
            select(Exercise.answer)
            .where(*base_filter)
            .group_by(Exercise.answer)
            .having(func.count() >= group_size)
            .order_by(func.random())
            .limit(num_groups)
        ).subquery()

        rn = func.row_number().over(
            partition_by=Exercise.answer,
            order_by=func.random(),
        ).label("rn")

        inner = (
            select(Exercise.id, rn)
            .where(
                Exercise.category_id == category_id,
                Exercise.answer.in_(select(eligible_sq.c.answer)),
            )
        )
        if exclude_ids:
            inner = inner.where(Exercise.id.notin_(exclude_ids))
        inner_sq = inner.subquery()

        statement = (
            select(Exercise)
            .join(inner_sq, Exercise.id == inner_sq.c.id)
            .where(inner_sq.c.rn <= group_size)
        )

        result = await self.session.execute(statement)
        return result.scalars().all()

from collections.abc import Sequence

from sqlalchemy import String, case, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Exercise, UserAnswer
from app.repositories import BaseRepository


class ExerciseRepository(BaseRepository[Exercise]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Exercise)

    async def get_random_unseen(
            self,
            category_id: int,
            user_id: int,
            limit: int,
            filters: list | None = None,
            *, distinct_on_answer: bool = False,
    ) -> Sequence[Exercise]:
        """Возвращает случайные активные упражнения, которые юзер ещё не решал.

        Пустой результат означает, что все задачи в категории решены хотя бы раз.
        Если distinct_on_answer=True — DISTINCT ON (answer), по 1 случайному unseen на тип.
        """
        answered_sq = (
            select(UserAnswer.exercise_id)
            .where(UserAnswer.user_id == user_id)
            .distinct()
            .subquery()
        )
        statement = (
            select(Exercise)
            .where(
                Exercise.category_id == category_id,
                Exercise.is_active.is_(True),
                Exercise.id.notin_(select(answered_sq.c.exercise_id)),
            )
        )
        if filters:
            statement = statement.where(*filters)
        if distinct_on_answer:
            statement = statement.distinct(Exercise.answer).order_by(Exercise.answer, func.random())
        else:
            statement = statement.order_by(func.random())
        statement = statement.limit(limit)
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_random_distinct_group_filler(
        self,
        category_id: int,
        limit: int,
        exclude_ids: list[int] | None = None,
        exclude_group_ids: list | None = None,
    ) -> Sequence[Exercise]:
        """Получает случайные упражнения с уникальными group_id, исключая указанные ID и группы."""
        distinct_group = func.coalesce(
            Exercise.group_id.cast(String),
            func.gen_random_uuid().cast(String),
        )

        query = (
            select(Exercise)
            .where(Exercise.category_id == category_id)
            .distinct(distinct_group)
            .order_by(distinct_group, func.random())
            .limit(limit)
        )

        if exclude_ids:
            query = query.where(Exercise.id.notin_(exclude_ids))

        if exclude_group_ids:
            query = query.where(
                (Exercise.group_id.is_(None)) | (~Exercise.group_id.in_(exclude_group_ids)),
            )

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_exam_22_exercises(self, category_id: int, user_id: int) -> Sequence[Exercise]:
        """Возвращает 5 совместимых упражнений для exam-режима задания 22.

        Использует рекурсивный CTE, который гарантирует:
        - ответы (found_devices) 5 предложений взаимно не пересекаются с present-устройствами других
        - other_devices никогда не попадут в варианты ответа
        - суммарное число distinct present-устройств <= 19, то есть хватит 4 дистракторов из 23

        Unseen exercises приоритизируются через ORDER BY is_seen, random().
        """
        sql = text("""
            WITH RECURSIVE
            answered AS (
                SELECT DISTINCT exercise_id
                FROM user_answers
                WHERE user_id = :user_id AND category_id = :category_id
            ),
            base_data AS (
                SELECT
                    e.id,
                    string_to_array(e.answer, ';') AS a_arr,
                    (string_to_array(e.answer, ';') ||
                     COALESCE(ARRAY(SELECT jsonb_array_elements_text(e.content->'other_devices')), '{}')) AS p_arr,
                    CASE WHEN a.exercise_id IS NULL THEN 0 ELSE 1 END AS is_seen
                FROM exercises e
                LEFT JOIN answered a ON e.id = a.exercise_id
                WHERE e.category_id = :category_id AND e.is_active = true
            ),
            exam_path AS (
                SELECT * FROM (
                    SELECT
                        ARRAY[id] AS ids,
                        a_arr AS c_a,
                        p_arr AS c_p,
                        1 AS depth
                    FROM base_data
                    ORDER BY is_seen, random()
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
                    ORDER BY b.is_seen, random()
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
        stmt = select(Exercise).from_statement(sql.bindparams(category_id=category_id, user_id=user_id))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_random_unseen_by_group(
        self,
        category_id: int,
        user_id: int,
        limit: int,
        filters: list | None = None,
    ) -> Sequence[Exercise]:
        """One random exercise per unseen group from target category.

        Cross-category unseen check: a group is "seen" if the user answered
        ANY exercise with that group_id (even from a different category).
        Exercises with NULL group_id fall back to per-exercise unseen check.
        """
        seen_groups_sq = (
            select(Exercise.group_id)
            .join(UserAnswer, UserAnswer.exercise_id == Exercise.id)
            .where(
                UserAnswer.user_id == user_id,
                Exercise.group_id.isnot(None),
            )
            .distinct()
            .subquery()
        )

        seen_exercises_sq = (
            select(UserAnswer.exercise_id)
            .where(UserAnswer.user_id == user_id)
            .distinct()
            .subquery()
        )

        distinct_group = func.coalesce(
            Exercise.group_id.cast(String),
            func.gen_random_uuid().cast(String),
        )

        statement = (
            select(Exercise)
            .outerjoin(seen_groups_sq, Exercise.group_id == seen_groups_sq.c.group_id)
            .outerjoin(seen_exercises_sq, Exercise.id == seen_exercises_sq.c.exercise_id)
            .where(
                Exercise.category_id == category_id,
                Exercise.is_active.is_(True),
                or_(
                    Exercise.group_id.isnot(None) & seen_groups_sq.c.group_id.is_(None),
                    Exercise.group_id.is_(None) & seen_exercises_sq.c.exercise_id.is_(None),
                ),
            )
        )
        if filters:
            statement = statement.where(*filters)
        statement = (
            statement
            .distinct(distinct_group)
            .order_by(distinct_group, func.random())
            .limit(limit)
        )

        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_random_by_group_ids(
        self,
        category_id: int,
        group_ids: Sequence,
        exclude_ids: set[int] | None = None,
        filters: list | None = None,
    ) -> Sequence[Exercise]:
        """One random exercise per group_id from target category."""
        if not group_ids:
            return []

        statement = (
            select(Exercise)
            .where(
                Exercise.category_id == category_id,
                Exercise.is_active.is_(True),
                Exercise.group_id.in_(group_ids),
            )
            .distinct(Exercise.group_id)
            .order_by(Exercise.group_id, func.random())
        )
        if exclude_ids:
            statement = statement.where(Exercise.id.notin_(exclude_ids))
        if filters:
            statement = statement.where(*filters)

        result = await self.session.execute(statement)
        return result.scalars().all()

    async def get_exercises_by_answers_unseen_first(
        self,
        category_id: int,
        user_id: int,
        answers: set[str],
        per_answer_limit: int,
        exclude_ids: set[int] | None = None,
    ) -> Sequence[Exercise]:
        """Batch fetch exercises for multiple answers, unseen first. One SQL query.

        Returns up to per_answer_limit exercises per answer,
        with unseen exercises prioritized over seen ones.
        """
        if not answers:
            return []

        answered_sq = (
            select(UserAnswer.exercise_id)
            .where(UserAnswer.user_id == user_id, UserAnswer.category_id == category_id)
            .distinct()
            .subquery()
        )

        is_seen = case(
            (answered_sq.c.exercise_id.is_(None), 0),
            else_=1,
        )

        rn = func.row_number().over(
            partition_by=Exercise.answer,
            order_by=(is_seen, func.random()),
        ).label("rn")

        inner = (
            select(Exercise.id, rn)
            .outerjoin(answered_sq, Exercise.id == answered_sq.c.exercise_id)
            .where(
                Exercise.category_id == category_id,
                Exercise.is_active.is_(True),
                Exercise.answer.in_(answers),
            )
        )
        if exclude_ids:
            inner = inner.where(Exercise.id.notin_(exclude_ids))
        inner_sq = inner.subquery()

        statement = (
            select(Exercise)
            .join(inner_sq, Exercise.id == inner_sq.c.id)
            .where(inner_sq.c.rn <= per_answer_limit)
        )

        result = await self.session.execute(statement)
        return result.scalars().all()

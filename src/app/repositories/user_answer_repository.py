
from collections.abc import Sequence

from sqlalchemy import Row, case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Exercise, UserAnswer
from app.repositories import BaseRepository


class UserAnswerRepository(BaseRepository[UserAnswer]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserAnswer)

    async def get_answered_exercise_ids(self, user_id: int, category_id: int) -> set[int]:
        statement = (
            select(distinct(UserAnswer.exercise_id))
            .where(
                UserAnswer.user_id == user_id,
                UserAnswer.category_id == category_id,
            )
        )
        result = await self.session.execute(statement)
        return set(result.scalars().all())

    async def get_exercise_stats(
        self, user_id: int, category_id: int, window_size: int = 5,
        filters: list | None = None,
    ) -> Sequence[Row]:
        """Возвращает статистику по последним window_size ответам на каждое упражнение.

        Каждая строка: (exercise_id, n_correct, n_wrong, avg_solve_time, last_attempt_at).
        Если filters переданы — JOIN к Exercise и применение фильтров.
        """
        rn = func.row_number().over(
            partition_by=UserAnswer.exercise_id,
            order_by=(UserAnswer.created_at.desc(), UserAnswer.id.desc()),
        ).label("rn")

        ranked_query = (
            select(
                UserAnswer.exercise_id,
                UserAnswer.is_correct,
                UserAnswer.solve_time,
                UserAnswer.created_at,
                rn,
            )
            .where(
                UserAnswer.user_id == user_id,
                UserAnswer.category_id == category_id,
            )
        )

        if filters:
            ranked_query = (
                ranked_query
                .join(Exercise, Exercise.id == UserAnswer.exercise_id)
                .where(*filters)
            )

        ranked = ranked_query.subquery()

        statement = (
            select(
                ranked.c.exercise_id,
                func.sum(case((ranked.c.is_correct, 1), else_=0)).label("n_correct"),
                func.sum(case((~ranked.c.is_correct, 1), else_=0)).label("n_wrong"),
                func.avg(ranked.c.solve_time).label("avg_solve_time"),
                func.max(ranked.c.created_at).label("last_attempt_at"),
            )
            .where(ranked.c.rn <= window_size)
            .group_by(ranked.c.exercise_id)
        )
        result = await self.session.execute(statement)
        return result.all()

    async def get_group_stats(
        self,
        user_id: int,
        target_category_id: int,
        window_size: int = 5,
        filters: list | None = None,
    ) -> Sequence[Row]:
        """Cross-category per-group stats for Thompson scoring.

        Finds group_ids present in target_category, then aggregates user_answers
        across ALL categories sharing those group_ids.
        Returns: (exercise_id [=group_id], n_correct, n_wrong, avg_solve_time, last_attempt_at).
        """
        target_groups_q = (
            select(Exercise.group_id)
            .where(
                Exercise.category_id == target_category_id,
                Exercise.is_active.is_(True),
                Exercise.group_id.isnot(None),
            )
        )
        if filters:
            target_groups_q = target_groups_q.where(*filters)
        target_groups = target_groups_q.distinct().subquery()

        group_exercises = (
            select(Exercise.id.label("exercise_id"), Exercise.group_id)
            .join(target_groups, Exercise.group_id == target_groups.c.group_id)
            .where(Exercise.is_active.is_(True))
        ).subquery()

        rn = func.row_number().over(
            partition_by=UserAnswer.exercise_id,
            order_by=(UserAnswer.created_at.desc(), UserAnswer.id.desc()),
        ).label("rn")

        ranked = (
            select(
                group_exercises.c.group_id,
                UserAnswer.is_correct,
                UserAnswer.solve_time,
                UserAnswer.created_at,
                rn,
            )
            .select_from(UserAnswer)
            .join(group_exercises, UserAnswer.exercise_id == group_exercises.c.exercise_id)
            .where(UserAnswer.user_id == user_id)
        ).subquery()

        statement = (
            select(
                ranked.c.group_id.label("exercise_id"),
                func.sum(case((ranked.c.is_correct, 1), else_=0)).label("n_correct"),
                func.sum(case((~ranked.c.is_correct, 1), else_=0)).label("n_wrong"),
                func.avg(ranked.c.solve_time).label("avg_solve_time"),
                func.max(ranked.c.created_at).label("last_attempt_at"),
            )
            .where(ranked.c.rn <= window_size)
            .group_by(ranked.c.group_id)
        )

        result = await self.session.execute(statement)
        return result.all()

    async def get_recent_results(
        self, user_id: int, category_ids: Sequence[int], limit: int = 5,
    ) -> dict[int, list[bool]]:
        """Returns last `limit` is_correct values per category_id, newest first."""
        if not category_ids:
            return {}
        rn = func.row_number().over(
            partition_by=UserAnswer.category_id,
            order_by=(UserAnswer.created_at.desc(), UserAnswer.id.desc()),
        ).label("rn")

        ranked = (
            select(
                UserAnswer.category_id,
                UserAnswer.is_correct,
                rn,
            )
            .where(
                UserAnswer.user_id == user_id,
                UserAnswer.category_id.in_(category_ids),
            )
        ).subquery()

        stmt = (
            select(ranked.c.category_id, ranked.c.is_correct)
            .where(ranked.c.rn <= limit)
            .order_by(ranked.c.category_id, ranked.c.rn)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        results_map: dict[int, list[bool]] = {}
        for cat_id, is_correct in rows:
            results_map.setdefault(cat_id, []).append(is_correct)
        return results_map

    async def get_answer_group_stats(
        self, user_id: int, category_id: int, min_group_size: int, window_size: int = 5,
    ) -> Sequence[Row]:
        """Per-answer eligibility + aggregated user stats in one query.

        Returns: (answer, total, unseen_count, n_correct, n_wrong, avg_solve_time, last_attempt_at).
        Only answers with total active exercises >= min_group_size.
        """
        answered_sq = (
            select(UserAnswer.exercise_id)
            .where(UserAnswer.user_id == user_id, UserAnswer.category_id == category_id)
            .distinct()
            .subquery()
        )

        answer_pool = (
            select(
                Exercise.answer.label("answer"),
                func.count().label("total"),
                func.sum(
                    case((answered_sq.c.exercise_id.is_(None), 1), else_=0),
                ).label("unseen_count"),
            )
            .outerjoin(answered_sq, Exercise.id == answered_sq.c.exercise_id)
            .where(Exercise.category_id == category_id, Exercise.is_active.is_(True))
            .group_by(Exercise.answer)
            .having(func.count() >= min_group_size)
        ).subquery()

        rn = func.row_number().over(
            partition_by=UserAnswer.exercise_id,
            order_by=(UserAnswer.created_at.desc(), UserAnswer.id.desc()),
        ).label("rn")

        ranked = (
            select(
                UserAnswer.exercise_id,
                UserAnswer.is_correct,
                UserAnswer.solve_time,
                UserAnswer.created_at,
                rn,
            )
            .where(UserAnswer.user_id == user_id, UserAnswer.category_id == category_id)
        ).subquery()

        answer_stats = (
            select(
                Exercise.answer.label("answer"),
                func.sum(case((ranked.c.is_correct, 1), else_=0)).label("n_correct"),
                func.sum(case((~ranked.c.is_correct, 1), else_=0)).label("n_wrong"),
                func.avg(ranked.c.solve_time).label("avg_solve_time"),
                func.max(ranked.c.created_at).label("last_attempt_at"),
            )
            .select_from(ranked)
            .join(Exercise, Exercise.id == ranked.c.exercise_id)
            .where(ranked.c.rn <= window_size, Exercise.category_id == category_id)
            .group_by(Exercise.answer)
        ).subquery()

        statement = select(
            answer_pool.c.answer,
            answer_pool.c.total,
            answer_pool.c.unseen_count,
            func.coalesce(answer_stats.c.n_correct, 0).label("n_correct"),
            func.coalesce(answer_stats.c.n_wrong, 0).label("n_wrong"),
            answer_stats.c.avg_solve_time,
            answer_stats.c.last_attempt_at,
        ).outerjoin(answer_stats, answer_pool.c.answer == answer_stats.c.answer)

        result = await self.session.execute(statement)
        return result.all()

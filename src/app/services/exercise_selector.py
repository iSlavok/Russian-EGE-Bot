import math
import random
import statistics
from collections.abc import Container, Sequence
from datetime import UTC, datetime

from app.models import Exercise
from app.repositories import ExerciseRepository, UserAnswerRepository
from app.repositories.exercise_filters import answer_eq, answer_ne, content_eq, content_exists

STATS_WINDOW_SIZE = 5


class ExerciseSelector:
    def __init__(
        self,
        exercise_repository: ExerciseRepository,
        answer_repository: UserAnswerRepository,
    ) -> None:
        self._exercise_repository = exercise_repository
        self._answer_repository = answer_repository

    async def select_smart(
            self,
            category_id: int,
            user_id: int,
            limit: int = 1,
            filters: list | None = None,
    ) -> Sequence[Exercise]:
        unseen = await self._exercise_repository.get_random_unseen(
            category_id, user_id, limit, filters=filters,
        )
        if len(unseen) >= limit:
            return unseen

        exclude_ids = {ex.id for ex in unseen}
        thompson = await self._select_thompson(
            category_id, user_id, limit - len(unseen), exclude_ids, filters=filters,
        )
        return [*unseen, *thompson]

    async def select_smart_by_group(
        self,
        category_id: int,
        user_id: int,
        limit: int = 1,
        filters: list | None = None,
    ) -> Sequence[Exercise]:
        """Smart-select scoring group_id (not individual exercises) using cross-category stats.

        Phase 1: unseen groups (cross-category check).
        Phase 2: Thompson on groups with cross-category stats.
        Fallback: regular Thompson for NULL group_id exercises.
        """
        unseen = await self._exercise_repository.get_random_unseen_by_group(
            category_id, user_id, limit, filters,
        )
        if len(unseen) >= limit:
            return unseen

        exclude_groups = {ex.group_id for ex in unseen if ex.group_id is not None}
        exclude_ids = {ex.id for ex in unseen}
        selected = list(unseen)

        group_stats = await self._answer_repository.get_group_stats(
            user_id, category_id, STATS_WINDOW_SIZE, filters,
        )
        if group_stats:
            scored = self._compute_thompson_scores(group_stats, exclude_groups)
            top_groups = [gid for gid, _ in scored[: limit - len(selected)]]
            if top_groups:
                group_exs = await self._exercise_repository.get_random_by_group_ids(
                    category_id, top_groups, exclude_ids, filters,
                )
                selected.extend(group_exs)

        if len(selected) < limit:
            remaining = limit - len(selected)
            all_exclude = {ex.id for ex in selected}
            thompson = await self._select_thompson(
                category_id, user_id, remaining, all_exclude, filters,
            )
            selected.extend(thompson)

        return selected

    async def select_by_answer(
        self, category_id: int, user_id: int, answer: str, limit: int,
    ) -> Sequence[Exercise]:
        return await self.select_smart(category_id, user_id, limit, [answer_eq(answer)])

    async def select_excluding_answer(
        self, category_id: int, user_id: int, exclude: str, limit: int,
    ) -> Sequence[Exercise]:
        return await self.select_smart(category_id, user_id, limit, [answer_ne(exclude)])

    async def select_by_content_field(
        self, category_id: int, user_id: int, field: str, limit: int,
    ) -> Sequence[Exercise]:
        return await self.select_smart(category_id, user_id, limit, [content_exists(field)])

    async def select_by_content_value(
        self, category_id: int, user_id: int, field: str, value: str, limit: int,
    ) -> Sequence[Exercise]:
        return await self.select_smart(category_id, user_id, limit, [content_eq(field, value)])

    async def select_by_answer_and_content(
        self, category_id: int, user_id: int, answer: str, field: str, value: str, limit: int,
    ) -> Sequence[Exercise]:
        return await self.select_smart(
            category_id, user_id, limit, [answer_eq(answer), content_eq(field, value)],
        )

    async def select_smart_same_answer_groups(
        self,
        category_id: int,
        user_id: int,
        group_size: int,
        num_groups: int,
    ) -> list[list[Exercise]]:
        """Smart-select num_groups групп по group_size упражнений с одинаковым answer.

        Допускает одинаковые answer в разных группах (если хватает упражнений).
        Phase 1: answer-level stats + eligibility (1 SQL).
        Phase 2: Thompson at answer level (Python).
        Phase 3: batch fetch exercises unseen-first (1 SQL).
        """
        answer_stats = await self._answer_repository.get_answer_group_stats(
            user_id, category_id, min_group_size=group_size,
        )
        if not answer_stats:
            return []

        selected_answers = self._pick_answers_thompson(answer_stats, group_size, num_groups)
        if not selected_answers:
            return []

        answer_demand: dict[str, int] = {}
        for answer in selected_answers:
            answer_demand[answer] = answer_demand.get(answer, 0) + group_size
        max_per_answer = max(answer_demand.values())

        exercises = await self._exercise_repository.get_exercises_by_answers_unseen_first(
            category_id, user_id, set(answer_demand.keys()), max_per_answer,
        )

        by_answer: dict[str, list[Exercise]] = {}
        for ex in exercises:
            by_answer.setdefault(ex.answer, []).append(ex)

        answer_offset: dict[str, int] = {}
        groups: list[list[Exercise]] = []
        for answer in selected_answers:
            offset = answer_offset.get(answer, 0)
            available = by_answer.get(answer, [])
            group = available[offset:offset + group_size]
            if len(group) < group_size:
                continue
            groups.append(group)
            answer_offset[answer] = offset + group_size

        return groups

    @staticmethod
    def _pick_answers_thompson(
        answer_stats: Sequence,
        group_size: int,
        num_groups: int,
    ) -> list[str]:
        """Pick num_groups answers via Thompson sampling at answer level.

        Allows same answer multiple times if capacity allows.
        """
        remaining_capacity: dict[str, int] = {row.answer: int(row.total) for row in answer_stats}
        selected: list[str] = []

        for _ in range(num_groups):
            scored: list[tuple[str, float]] = []

            for row in answer_stats:
                if remaining_capacity.get(row.answer, 0) < group_size:
                    continue

                n_correct = int(row.n_correct)
                n_wrong = int(row.n_wrong)

                if n_correct == 0 and n_wrong == 0:
                    score = 1.0 + random.random()
                else:
                    theta = random.betavariate(n_wrong + 1, n_correct + 1)
                    if row.last_attempt_at is not None:
                        days_since = (
                            datetime.now(UTC) - row.last_attempt_at
                        ).total_seconds() / 86400
                        recency_boost = 1.0 + math.log1p(max(0.0, days_since)) / 10.0
                    else:
                        recency_boost = 1.5
                    score = theta * recency_boost

                scored.append((row.answer, score))

            if not scored:
                break

            scored.sort(key=lambda x: x[1], reverse=True)
            best = scored[0][0]
            selected.append(best)
            remaining_capacity[best] -= group_size

        return selected

    async def select_smart_distinct_answer(
        self,
        category_id: int,
        user_id: int,
        limit: int,
        filters: list | None = None,
    ) -> Sequence[Exercise]:
        """Smart-select с гарантией уникальных answer среди результатов.

        Phase 1: unseen с DISTINCT ON (answer) — один случайный unseen на тип.
        Phase 2: Thompson scoring + дедупликация по answer (если unseen < limit).
        """
        unseen = await self._exercise_repository.get_random_unseen(
            category_id, user_id, limit, filters=filters, distinct_on_answer=True,
        )
        if len(unseen) >= limit:
            return unseen

        seen_answers = {ex.answer for ex in unseen}
        exclude_ids = {ex.id for ex in unseen}
        selected: list[Exercise] = list(unseen)

        stats_rows = await self._answer_repository.get_exercise_stats(
            user_id, category_id, STATS_WINDOW_SIZE, filters=filters,
        )
        if not stats_rows:
            return selected

        scored = self._compute_thompson_scores(stats_rows, exclude_ids)
        candidate_ids = [eid for eid, _ in scored]
        candidates = await self._exercise_repository.get_by_ids(candidate_ids)
        candidates_map = {ex.id: ex for ex in candidates}

        for eid, _ in scored:
            ex = candidates_map.get(eid)
            if ex is not None and ex.answer not in seen_answers:
                seen_answers.add(ex.answer)
                selected.append(ex)
                if len(selected) >= limit:
                    break

        return selected

    @staticmethod
    def _compute_thompson_scores(
        stats_rows: Sequence, exclude_ids: Container | None = None,
    ) -> list[tuple]:
        """Скорит упражнения через Thompson sampling. Возвращает (exercise_id, score) по убыванию."""
        avg_times = [
            float(row.avg_solve_time)
            for row in stats_rows
            if row.avg_solve_time is not None and row.avg_solve_time > 0
        ]
        category_median = statistics.median(avg_times) if avg_times else 1.0

        now = datetime.now(UTC)
        scored: list[tuple[int, float]] = []

        for row in stats_rows:
            if exclude_ids and row.exercise_id in exclude_ids:
                continue

            n_correct = int(row.n_correct)
            n_wrong = int(row.n_wrong)

            theta = random.betavariate(n_wrong + 1, n_correct + 1)

            days_since = (now - row.last_attempt_at).total_seconds() / 86400
            recency_boost = 1.0 + math.log1p(max(0.0, days_since)) / 10.0

            avg_time = float(row.avg_solve_time) if row.avg_solve_time else 0.0
            time_ratio = (avg_time / category_median - 1.0) if category_median > 0 else 0.0
            time_factor = 1.0 + 0.3 * max(0.0, min(time_ratio, 2.0))

            score = theta * recency_boost * time_factor
            scored.append((row.exercise_id, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    async def _select_thompson(
            self,
            category_id: int,
            user_id: int,
            limit: int,
            exclude_ids: set[int] | None = None,
            filters: list | None = None,
    ) -> Sequence[Exercise]:
        stats_rows = await self._answer_repository.get_exercise_stats(
            user_id, category_id, window_size=STATS_WINDOW_SIZE, filters=filters,
        )
        if not stats_rows:
            return []

        scored = self._compute_thompson_scores(stats_rows, exclude_ids)
        top_ids = [eid for eid, _ in scored[:limit]]

        return await self._exercise_repository.get_by_ids(top_ids)

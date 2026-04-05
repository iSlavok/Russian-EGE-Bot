from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING

from app.models import Category, UserCategoryStat
from app.repositories import CategoryRepository, UserAnswerRepository
from app.repositories.user_category_stat_repository import UserCategoryStatRepository
from app.repositories.user_stat_repository import UserStatRepository
from app.schemas.stats_schemas import CategoryStatItemDTO, ProfileSummaryDTO

if TYPE_CHECKING:
    from collections.abc import Sequence

MSK = timezone(timedelta(hours=3))


def _today_msk() -> date:
    return datetime.now(MSK).date()


def _percent(correct: int, total: int) -> int:
    return round(correct * 100 / total) if total > 0 else 0


class StatsService:
    def __init__(
        self,
        user_stat_repository: UserStatRepository,
        user_category_stat_repository: UserCategoryStatRepository,
        category_repository: CategoryRepository,
        user_answer_repository: UserAnswerRepository,
    ) -> None:
        self._user_stat_repo = user_stat_repository
        self._user_category_stat_repo = user_category_stat_repository
        self._category_repo = category_repository
        self._user_answer_repo = user_answer_repository

    async def record_answer_stats(
        self,
        user_id: int,
        category_id: int,
        is_correct: bool,  # noqa: FBT001
        exercise_ids: list[int],
    ) -> None:
        today = _today_msk()
        await self._user_stat_repo.increment_answer(user_id, is_correct=is_correct, answer_date=today)

        answered_ids = await self._user_answer_repo.get_answered_exercise_ids(user_id, category_id)
        is_new = not any(eid in answered_ids for eid in exercise_ids)

        await self._user_category_stat_repo.increment_answer(
            user_id, category_id, is_correct=is_correct, is_new_exercise=is_new,
        )

    async def get_profile_summary(self, user_id: int, full_name: str, registered_at: datetime) -> ProfileSummaryDTO:
        stat = await self._user_stat_repo.get_or_create(user_id)
        daily_streak = self._get_actual_daily_streak(stat.current_daily_streak, stat.last_answer_date)
        pct = _percent(stat.total_correct, stat.total_answered)
        return ProfileSummaryDTO(
            full_name=full_name,
            registered_at=registered_at,
            total_answered=stat.total_answered,
            total_correct=stat.total_correct,
            correct_percent=pct,
            current_streak=stat.current_streak,
            max_streak=stat.max_streak,
            current_daily_streak=daily_streak,
        )

    async def get_children_stats(self, user_id: int, parent_id: int | None) -> list[CategoryStatItemDTO]:
        """Get children of parent with aggregated stats from all leaf descendants."""
        if parent_id is None:
            children: Sequence[Category] = await self._category_repo.get_roots()
        else:
            parent = await self._category_repo.get_by_id_with_children(parent_id)
            children = parent.children if parent else []

        stats_map = await self._get_user_stats_map(user_id)

        result: list[CategoryStatItemDTO] = []
        for child in children:
            total, correct = await self._aggregate_leaf_stats(child.id, stats_map)
            result.append(CategoryStatItemDTO(
                category_id=child.id,
                name=child.name,
                is_ege_task=child.is_ege_task,
                total_answered=total,
                total_correct=correct,
                percent=_percent(correct, total),
            ))
        return result

    async def get_category_aggregated_stats(self, user_id: int, category_id: int) -> CategoryStatItemDTO:
        """Get aggregated stats for a single category (sum of all leaf descendants)."""
        cat = await self._category_repo.get_by_id(category_id)
        stats_map = await self._get_user_stats_map(user_id)
        total, correct = await self._aggregate_leaf_stats(category_id, stats_map)
        return CategoryStatItemDTO(
            category_id=category_id,
            name=cat.name if cat else "???",
            is_ege_task=cat.is_ege_task if cat else False,
            total_answered=total,
            total_correct=correct,
            percent=_percent(correct, total),
        )

    async def _get_user_stats_map(self, user_id: int) -> dict[int, UserCategoryStat]:
        cat_stats = await self._user_category_stat_repo.get_all_by_user(user_id)
        return {s.category_id: s for s in cat_stats}

    async def _aggregate_leaf_stats(
        self, category_id: int, stats_map: dict[int, UserCategoryStat],
    ) -> tuple[int, int]:
        tree = await self._category_repo.get_by_id_with_tree(category_id)
        child_ids = {c.parent_id for c in tree if c.parent_id is not None}
        leaf_ids = [c.id for c in tree if c.id not in child_ids]
        total = sum(stats_map[lid].total_answered for lid in leaf_ids if lid in stats_map)
        correct = sum(stats_map[lid].total_correct for lid in leaf_ids if lid in stats_map)
        return total, correct

    @staticmethod
    def _get_actual_daily_streak(current_daily_streak: int, last_answer_date: date | None) -> int:
        if last_answer_date is None:
            return 0
        today = _today_msk()
        delta = (today - last_answer_date).days
        if delta <= 1:
            return current_daily_streak
        return 0

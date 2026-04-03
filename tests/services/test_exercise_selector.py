import random
from collections import namedtuple
from datetime import UTC, datetime, timedelta

from app.repositories.exercise_filters import answer_eq
from app.services.exercise_selector import ExerciseSelector

# ---------------------------------------------------------------------------
# Mock rows for unit-testing static methods
# ---------------------------------------------------------------------------

StatsRow = namedtuple(
    "StatsRow",
    ["exercise_id", "n_correct", "n_wrong", "avg_solve_time", "last_attempt_at"],
)

AnswerStatsRow = namedtuple(
    "AnswerStatsRow",
    ["answer", "total", "unseen_count", "n_correct", "n_wrong", "avg_solve_time", "last_attempt_at"],
)


# ===================================================================
# _compute_thompson_scores  (unit tests — no DB)
# ===================================================================

class TestComputeThompsonScores:
    def test_returns_sorted_descending(self):
        random.seed(42)
        now = datetime.now(UTC)
        rows = [
            StatsRow(1, 10, 0, 5.0, now - timedelta(days=1)),
            StatsRow(2, 0, 10, 5.0, now - timedelta(days=1)),
        ]
        scored = ExerciseSelector._compute_thompson_scores(rows)

        assert scored[0][1] >= scored[1][1]

    def test_exclude_ids_filters(self):
        random.seed(42)
        now = datetime.now(UTC)
        rows = [
            StatsRow(1, 5, 5, 5.0, now),
            StatsRow(2, 5, 5, 5.0, now),
            StatsRow(3, 5, 5, 5.0, now),
        ]
        scored = ExerciseSelector._compute_thompson_scores(rows, exclude_ids={1, 3})

        assert len(scored) == 1
        assert scored[0][0] == 2

    def test_all_excluded_returns_empty(self):
        now = datetime.now(UTC)
        rows = [StatsRow(1, 5, 5, 5.0, now)]

        scored = ExerciseSelector._compute_thompson_scores(rows, exclude_ids={1})

        assert scored == []

    def test_no_exclude_returns_all(self):
        random.seed(42)
        now = datetime.now(UTC)
        rows = [
            StatsRow(1, 5, 5, 5.0, now),
            StatsRow(2, 5, 5, 5.0, now),
        ]
        scored = ExerciseSelector._compute_thompson_scores(rows, exclude_ids=None)

        assert len(scored) == 2

    def test_avg_solve_time_none_handled(self):
        random.seed(42)
        now = datetime.now(UTC)
        rows = [StatsRow(1, 5, 5, None, now)]

        scored = ExerciseSelector._compute_thompson_scores(rows)

        assert len(scored) == 1
        assert scored[0][0] == 1

    def test_wrong_heavy_scores_higher(self):
        """Упражнения с бо́льшим числом ошибок должны чаще получать высокий скор."""
        now = datetime.now(UTC)
        row_good = StatsRow(1, 9, 1, 5.0, now)
        row_bad = StatsRow(2, 1, 9, 5.0, now)

        bad_wins = 0
        for i in range(200):
            random.seed(i)
            scored = ExerciseSelector._compute_thompson_scores([row_good, row_bad])
            if scored[0][0] == 2:
                bad_wins += 1

        assert bad_wins > 120

    def test_recency_boost_increases_with_age(self):
        """Давно не решавшиеся упражнения получают бо́льший recency_boost."""
        now = datetime.now(UTC)
        row_recent = StatsRow(1, 5, 5, 5.0, now)
        row_old = StatsRow(2, 5, 5, 5.0, now - timedelta(days=30))

        old_wins = 0
        for i in range(200):
            random.seed(i)
            scored = ExerciseSelector._compute_thompson_scores([row_recent, row_old])
            score_map = dict(scored)
            if score_map[2] > score_map[1]:
                old_wins += 1

        assert old_wins > 80

    def test_time_factor_boosts_slow_exercises(self):
        """Упражнения с высоким avg_solve_time получают time_factor > 1."""
        now = datetime.now(UTC)
        row_fast = StatsRow(1, 5, 5, 2.0, now)
        row_slow = StatsRow(2, 5, 5, 20.0, now)

        slow_wins = 0
        for i in range(200):
            random.seed(i)
            scored = ExerciseSelector._compute_thompson_scores([row_fast, row_slow])
            score_map = dict(scored)
            if score_map[2] > score_map[1]:
                slow_wins += 1

        assert slow_wins > 80

    def test_single_row(self):
        random.seed(42)
        now = datetime.now(UTC)
        rows = [StatsRow(99, 3, 7, 12.0, now - timedelta(hours=6))]

        scored = ExerciseSelector._compute_thompson_scores(rows)

        assert len(scored) == 1
        assert scored[0][0] == 99
        assert scored[0][1] > 0

    def test_container_exclude_ids(self):
        """exclude_ids принимает любой Container — frozenset, list и т.д."""
        random.seed(42)
        now = datetime.now(UTC)
        rows = [StatsRow(1, 5, 5, 5.0, now), StatsRow(2, 5, 5, 5.0, now)]

        scored = ExerciseSelector._compute_thompson_scores(rows, exclude_ids=frozenset({1}))

        assert len(scored) == 1
        assert scored[0][0] == 2


# ===================================================================
# _pick_answers_thompson  (unit tests — no DB)
# ===================================================================

class TestPickAnswersThompson:
    def test_unseen_answers_prioritized(self):
        """Unseen (n_correct=0, n_wrong=0) получают score > 1.0 и выбираются первыми."""
        now = datetime.now(UTC)
        rows = [
            AnswerStatsRow("A", 10, 0, 8, 2, 5.0, now),
            AnswerStatsRow("B", 10, 10, 0, 0, None, None),
        ]

        b_wins = 0
        for i in range(100):
            random.seed(i)
            result = ExerciseSelector._pick_answers_thompson(rows, group_size=2, num_groups=1)
            if result == ["B"]:
                b_wins += 1

        assert b_wins > 50

    def test_capacity_decreases_allows_repeat(self):
        """Один answer может быть выбран несколько раз, если capacity позволяет."""
        random.seed(42)
        rows = [AnswerStatsRow("A", 6, 6, 0, 0, None, None)]

        result = ExerciseSelector._pick_answers_thompson(rows, group_size=3, num_groups=2)

        assert result == ["A", "A"]

    def test_skips_insufficient_capacity(self):
        """Answer с capacity < group_size пропускается."""
        random.seed(42)
        rows = [AnswerStatsRow("A", 3, 3, 0, 0, None, None)]

        result = ExerciseSelector._pick_answers_thompson(rows, group_size=3, num_groups=2)

        assert result == ["A"]

    def test_empty_when_no_eligible(self):
        random.seed(42)
        rows = [AnswerStatsRow("A", 1, 1, 0, 0, None, None)]

        result = ExerciseSelector._pick_answers_thompson(rows, group_size=3, num_groups=1)

        assert result == []

    def test_multiple_answers_picked(self):
        random.seed(42)
        rows = [
            AnswerStatsRow("A", 5, 5, 0, 0, None, None),
            AnswerStatsRow("B", 5, 5, 0, 0, None, None),
            AnswerStatsRow("C", 5, 5, 0, 0, None, None),
        ]

        result = ExerciseSelector._pick_answers_thompson(rows, group_size=2, num_groups=3)

        assert len(result) == 3
        assert set(result) <= {"A", "B", "C"}

    def test_last_attempt_none_gets_higher_recency(self):
        """last_attempt_at=None → recency_boost=1.5, выше чем у свежих."""
        now = datetime.now(UTC)
        rows = [
            AnswerStatsRow("A", 10, 0, 0, 10, 5.0, now),
            AnswerStatsRow("B", 10, 0, 0, 10, 5.0, None),
        ]

        b_wins = 0
        for i in range(200):
            random.seed(i)
            result = ExerciseSelector._pick_answers_thompson(rows, group_size=1, num_groups=1)
            if result == ["B"]:
                b_wins += 1

        assert b_wins > 60

    def test_stops_when_no_candidates(self):
        """Если после нескольких итераций все capacity исчерпаны — останавливается."""
        random.seed(42)
        rows = [
            AnswerStatsRow("A", 2, 2, 0, 0, None, None),
            AnswerStatsRow("B", 2, 2, 0, 0, None, None),
        ]

        result = ExerciseSelector._pick_answers_thompson(rows, group_size=2, num_groups=5)

        assert len(result) == 2


# ===================================================================
# select_smart  (integration tests — real DB)
# ===================================================================

class TestSelectSmart:
    async def test_all_unseen_returns_unseen(
        self, exercise_selector, user_factory, category_factory, exercise_factory,
    ):
        user = await user_factory()
        cat = await category_factory()
        ex1 = await exercise_factory(category_id=cat.id)
        ex2 = await exercise_factory(category_id=cat.id)

        result = await exercise_selector.select_smart(cat.id, user.id, limit=2)

        assert {e.id for e in result} == {ex1.id, ex2.id}

    async def test_partial_unseen_fills_with_thompson(
        self,
        exercise_selector,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        cat = await category_factory()
        seen = await exercise_factory(category_id=cat.id)
        unseen = await exercise_factory(category_id=cat.id)

        await user_answer_factory(user_id=user.id, exercise_id=seen.id, category_id=cat.id)

        result = await exercise_selector.select_smart(cat.id, user.id, limit=2)

        result_ids = {e.id for e in result}
        assert unseen.id in result_ids
        assert seen.id in result_ids
        assert len(result) == 2

    async def test_all_seen_returns_thompson(
        self,
        exercise_selector,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        cat = await category_factory()
        ex = await exercise_factory(category_id=cat.id)
        await user_answer_factory(user_id=user.id, exercise_id=ex.id, category_id=cat.id)

        result = await exercise_selector.select_smart(cat.id, user.id, limit=1)

        assert len(result) == 1
        assert result[0].id == ex.id

    async def test_empty_category_returns_empty(
        self, exercise_selector, user_factory, category_factory,
    ):
        user = await user_factory()
        cat = await category_factory()

        result = await exercise_selector.select_smart(cat.id, user.id, limit=1)

        assert list(result) == []

    async def test_no_duplicates(
        self,
        exercise_selector,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        """Unseen + Thompson не должны возвращать дубликаты."""
        user = await user_factory()
        cat = await category_factory()
        exs = [await exercise_factory(category_id=cat.id) for _ in range(3)]
        await user_answer_factory(user_id=user.id, exercise_id=exs[0].id, category_id=cat.id)
        await user_answer_factory(user_id=user.id, exercise_id=exs[1].id, category_id=cat.id)

        result = await exercise_selector.select_smart(cat.id, user.id, limit=3)

        result_ids = [e.id for e in result]
        assert len(result_ids) == len(set(result_ids))

    async def test_filters_propagated(
        self,
        exercise_selector,
        user_factory,
        category_factory,
        exercise_factory,
    ):
        user = await user_factory()
        cat = await category_factory()
        await exercise_factory(category_id=cat.id, answer="yes")
        await exercise_factory(category_id=cat.id, answer="no")

        result = await exercise_selector.select_smart(
            cat.id, user.id, limit=10, filters=[answer_eq("yes")],
        )

        assert all(e.answer == "yes" for e in result)

    async def test_limit_respected(
        self,
        exercise_selector,
        user_factory,
        category_factory,
        exercise_factory,
    ):
        user = await user_factory()
        cat = await category_factory()
        for _ in range(10):
            await exercise_factory(category_id=cat.id)

        result = await exercise_selector.select_smart(cat.id, user.id, limit=3)

        assert len(result) == 3


# ===================================================================
# select_smart_by_group  (integration tests — real DB)
# ===================================================================

class TestSelectSmartByGroup:
    async def test_phase1_sufficient_returns_early(
        self, exercise_selector, user_factory, category_factory, exercise_factory,
    ):
        """Достаточно unseen групп → возвращается сразу без Thompson."""
        user = await user_factory()
        cat = await category_factory()
        g1 = "11111111-1111-1111-1111-111111111111"
        g2 = "22222222-2222-2222-2222-222222222222"
        await exercise_factory(category_id=cat.id, group_id=g1)
        await exercise_factory(category_id=cat.id, group_id=g2)

        result = await exercise_selector.select_smart_by_group(cat.id, user.id, limit=2)

        assert len(result) == 2
        group_ids = {e.group_id for e in result}
        assert len(group_ids) == 2

    async def test_phase2_fills_from_thompson_groups(
        self,
        exercise_selector,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        """Unseen < limit → Phase 2 (Thompson на группах) добирает."""
        user = await user_factory()
        cat = await category_factory()
        g1 = "11111111-1111-1111-1111-111111111111"
        g2 = "22222222-2222-2222-2222-222222222222"
        ex1 = await exercise_factory(category_id=cat.id, group_id=g1)
        await exercise_factory(category_id=cat.id, group_id=g2)

        await user_answer_factory(user_id=user.id, exercise_id=ex1.id, category_id=cat.id)

        result = await exercise_selector.select_smart_by_group(cat.id, user.id, limit=2)

        assert len(result) == 2
        group_ids = {e.group_id for e in result}
        assert len(group_ids) == 2

    async def test_phase3_fallback_for_null_groups(
        self,
        exercise_selector,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        """Группы исчерпаны → fallback Thompson подбирает NULL group_id."""
        user = await user_factory()
        cat = await category_factory()
        g1 = "11111111-1111-1111-1111-111111111111"
        ex_g = await exercise_factory(category_id=cat.id, group_id=g1)
        ex_null = await exercise_factory(category_id=cat.id, group_id=None)

        await user_answer_factory(user_id=user.id, exercise_id=ex_g.id, category_id=cat.id)
        await user_answer_factory(user_id=user.id, exercise_id=ex_null.id, category_id=cat.id)

        result = await exercise_selector.select_smart_by_group(cat.id, user.id, limit=2)

        result_ids = {e.id for e in result}
        assert ex_g.id in result_ids
        assert ex_null.id in result_ids

    async def test_cross_category_unseen_check(
        self,
        exercise_selector,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        """Группа, решённая в drill-категории, исключается из exam-категории."""
        user = await user_factory()
        cat_drill = await category_factory(name="Drill")
        cat_exam = await category_factory(name="Exam")
        g1 = "11111111-1111-1111-1111-111111111111"
        g2 = "22222222-2222-2222-2222-222222222222"

        drill_ex = await exercise_factory(category_id=cat_drill.id, group_id=g1)
        await exercise_factory(category_id=cat_exam.id, group_id=g1)
        await exercise_factory(category_id=cat_exam.id, group_id=g2)

        await user_answer_factory(
            user_id=user.id, exercise_id=drill_ex.id, category_id=cat_drill.id,
        )

        result = await exercise_selector.select_smart_by_group(cat_exam.id, user.id, limit=1)

        assert len(result) == 1
        assert str(result[0].group_id) == g2

    async def test_empty_category_returns_empty(
        self, exercise_selector, user_factory, category_factory,
    ):
        user = await user_factory()
        cat = await category_factory()

        result = await exercise_selector.select_smart_by_group(cat.id, user.id, limit=1)

        assert list(result) == []

    async def test_filters_applied_all_phases(
        self,
        exercise_selector,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        """Фильтры применяются во всех фазах: unseen, group stats, fallback."""
        user = await user_factory()
        cat = await category_factory()
        g1 = "11111111-1111-1111-1111-111111111111"
        g2 = "22222222-2222-2222-2222-222222222222"
        await exercise_factory(category_id=cat.id, group_id=g1, answer="yes")
        await exercise_factory(category_id=cat.id, group_id=g2, answer="no")
        await exercise_factory(category_id=cat.id, group_id=None, answer="no")

        result = await exercise_selector.select_smart_by_group(
            cat.id, user.id, limit=10, filters=[answer_eq("yes")],
        )

        assert len(result) == 1
        assert result[0].answer == "yes"

    async def test_no_duplicates_across_phases(
        self,
        exercise_selector,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        """Упражнения из Phase 1 не дублируются в Phase 2/3."""
        user = await user_factory()
        cat = await category_factory()
        g1 = "11111111-1111-1111-1111-111111111111"
        g2 = "22222222-2222-2222-2222-222222222222"
        g3 = "33333333-3333-3333-3333-333333333333"
        await exercise_factory(category_id=cat.id, group_id=g1)
        ex2 = await exercise_factory(category_id=cat.id, group_id=g2)
        await exercise_factory(category_id=cat.id, group_id=g3)
        await exercise_factory(category_id=cat.id, group_id=None)

        await user_answer_factory(user_id=user.id, exercise_id=ex2.id, category_id=cat.id)

        result = await exercise_selector.select_smart_by_group(cat.id, user.id, limit=4)

        result_ids = [e.id for e in result]
        assert len(result_ids) == len(set(result_ids))

    async def test_all_groups_seen_falls_through_to_thompson(
        self,
        exercise_selector,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        """Все группы seen → Phase 2 Thompson скорит, Phase 3 fallback если нужно."""
        user = await user_factory()
        cat = await category_factory()
        g1 = "11111111-1111-1111-1111-111111111111"
        g2 = "22222222-2222-2222-2222-222222222222"
        ex1 = await exercise_factory(category_id=cat.id, group_id=g1)
        ex2 = await exercise_factory(category_id=cat.id, group_id=g2)

        await user_answer_factory(user_id=user.id, exercise_id=ex1.id, category_id=cat.id)
        await user_answer_factory(user_id=user.id, exercise_id=ex2.id, category_id=cat.id)

        result = await exercise_selector.select_smart_by_group(cat.id, user.id, limit=2)

        assert len(result) == 2

    async def test_cross_category_stats_influence_scoring(
        self,
        exercise_selector,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        """Drill-ответы влияют на приоритизацию exam-упражнений.

        Группа с ошибками в drill должна приоритизироваться выше группы с правильными ответами.
        """
        user = await user_factory()
        cat_drill = await category_factory(name="Drill")
        cat_exam = await category_factory(name="Exam")
        g_easy = "11111111-1111-1111-1111-111111111111"
        g_hard = "22222222-2222-2222-2222-222222222222"

        drill_easy = await exercise_factory(category_id=cat_drill.id, group_id=g_easy)
        drill_hard = await exercise_factory(category_id=cat_drill.id, group_id=g_hard)
        await exercise_factory(category_id=cat_exam.id, group_id=g_easy)
        await exercise_factory(category_id=cat_exam.id, group_id=g_hard)

        # Лёгкая группа: все ответы правильные
        for _ in range(5):
            await user_answer_factory(
                user_id=user.id, exercise_id=drill_easy.id, category_id=cat_drill.id,
                is_correct=True,
            )
        # Тяжёлая группа: все ответы неправильные
        for _ in range(5):
            await user_answer_factory(
                user_id=user.id, exercise_id=drill_hard.id, category_id=cat_drill.id,
                is_correct=False,
            )

        hard_first_count = 0
        for i in range(50):
            random.seed(i)
            result = await exercise_selector.select_smart_by_group(
                cat_exam.id, user.id, limit=1,
            )
            if result and str(result[0].group_id) == g_hard:
                hard_first_count += 1

        # Тяжёлая группа должна выбираться чаще
        assert hard_first_count > 25


# ===================================================================
# select_smart_distinct_answer  (integration tests — real DB)
# ===================================================================

class TestSelectSmartDistinctAnswer:
    async def test_all_unseen_returns_distinct_answers(
        self, exercise_selector, user_factory, category_factory, exercise_factory,
    ):
        user = await user_factory()
        cat = await category_factory()
        await exercise_factory(category_id=cat.id, answer="A")
        await exercise_factory(category_id=cat.id, answer="A")
        await exercise_factory(category_id=cat.id, answer="B")

        result = await exercise_selector.select_smart_distinct_answer(cat.id, user.id, limit=2)

        answers = {e.answer for e in result}
        assert answers == {"A", "B"}

    async def test_phase2_deduplicates_by_answer(
        self,
        exercise_selector,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        """Phase 2 (Thompson) пропускает упражнения с уже выбранным answer."""
        user = await user_factory()
        cat = await category_factory()
        ex_a1 = await exercise_factory(category_id=cat.id, answer="A")
        ex_a2 = await exercise_factory(category_id=cat.id, answer="A")
        ex_b = await exercise_factory(category_id=cat.id, answer="B")

        for ex in [ex_a1, ex_a2, ex_b]:
            await user_answer_factory(user_id=user.id, exercise_id=ex.id, category_id=cat.id)

        result = await exercise_selector.select_smart_distinct_answer(cat.id, user.id, limit=2)

        answers = [e.answer for e in result]
        assert len(set(answers)) == len(answers)

    async def test_empty_returns_empty(
        self, exercise_selector, user_factory, category_factory,
    ):
        user = await user_factory()
        cat = await category_factory()

        result = await exercise_selector.select_smart_distinct_answer(cat.id, user.id, limit=1)

        assert list(result) == []

    async def test_limit_caps_result(
        self,
        exercise_selector,
        user_factory,
        category_factory,
        exercise_factory,
    ):
        user = await user_factory()
        cat = await category_factory()
        for letter in "ABCDE":
            await exercise_factory(category_id=cat.id, answer=letter)

        result = await exercise_selector.select_smart_distinct_answer(cat.id, user.id, limit=3)

        assert len(result) == 3
        assert len({e.answer for e in result}) == 3


# ===================================================================
# select_smart_same_answer_groups  (integration tests — real DB)
# ===================================================================

class TestSelectSmartSameAnswerGroups:
    async def test_returns_groups_with_same_answer(
        self, exercise_selector, user_factory, category_factory, exercise_factory,
    ):
        user = await user_factory()
        cat = await category_factory()
        for _ in range(4):
            await exercise_factory(category_id=cat.id, answer="A")
        for _ in range(4):
            await exercise_factory(category_id=cat.id, answer="B")

        result = await exercise_selector.select_smart_same_answer_groups(
            cat.id, user.id, group_size=2, num_groups=2,
        )

        assert len(result) == 2
        for group in result:
            assert len(group) == 2
            answers = {e.answer for e in group}
            assert len(answers) == 1

    async def test_empty_when_no_eligible(
        self, exercise_selector, user_factory, category_factory, exercise_factory,
    ):
        """Недостаточно упражнений на один answer → пустой результат."""
        user = await user_factory()
        cat = await category_factory()
        await exercise_factory(category_id=cat.id, answer="A")

        result = await exercise_selector.select_smart_same_answer_groups(
            cat.id, user.id, group_size=3, num_groups=1,
        )

        assert result == []

    async def test_skips_incomplete_group(
        self, exercise_selector, user_factory, category_factory, exercise_factory,
    ):
        """Если упражнений хватает на 1 группу, но не на 2 — возвращает 1."""
        user = await user_factory()
        cat = await category_factory()
        for _ in range(3):
            await exercise_factory(category_id=cat.id, answer="A")

        result = await exercise_selector.select_smart_same_answer_groups(
            cat.id, user.id, group_size=3, num_groups=2,
        )

        assert len(result) == 1

    async def test_empty_category_returns_empty(
        self, exercise_selector, user_factory, category_factory,
    ):
        user = await user_factory()
        cat = await category_factory()

        result = await exercise_selector.select_smart_same_answer_groups(
            cat.id, user.id, group_size=2, num_groups=1,
        )

        assert result == []

    async def test_exercises_not_repeated_across_groups(
        self, exercise_selector, user_factory, category_factory, exercise_factory,
    ):
        """Упражнения не повторяются между группами одного answer."""
        user = await user_factory()
        cat = await category_factory()
        for _ in range(6):
            await exercise_factory(category_id=cat.id, answer="A")

        result = await exercise_selector.select_smart_same_answer_groups(
            cat.id, user.id, group_size=3, num_groups=2,
        )

        assert len(result) == 2
        all_ids = [e.id for group in result for e in group]
        assert len(all_ids) == len(set(all_ids))

    async def test_group_size_respected(
        self, exercise_selector, user_factory, category_factory, exercise_factory,
    ):
        user = await user_factory()
        cat = await category_factory()
        for _ in range(10):
            await exercise_factory(category_id=cat.id, answer="X")

        result = await exercise_selector.select_smart_same_answer_groups(
            cat.id, user.id, group_size=4, num_groups=2,
        )

        assert len(result) == 2
        for group in result:
            assert len(group) == 4


# ===================================================================
# Convenience wrappers  (integration — smoke tests only)
# ===================================================================

class TestConvenienceWrappers:
    async def test_select_by_answer(
        self, exercise_selector, user_factory, category_factory, exercise_factory,
    ):
        user = await user_factory()
        cat = await category_factory()
        await exercise_factory(category_id=cat.id, answer="yes")
        await exercise_factory(category_id=cat.id, answer="no")

        result = await exercise_selector.select_by_answer(cat.id, user.id, "yes", limit=10)

        assert all(e.answer == "yes" for e in result)

    async def test_select_excluding_answer(
        self, exercise_selector, user_factory, category_factory, exercise_factory,
    ):
        user = await user_factory()
        cat = await category_factory()
        await exercise_factory(category_id=cat.id, answer="yes")
        await exercise_factory(category_id=cat.id, answer="no")

        result = await exercise_selector.select_excluding_answer(cat.id, user.id, "yes", limit=10)

        assert all(e.answer != "yes" for e in result)

    async def test_select_by_content_field(
        self, exercise_selector, user_factory, category_factory, exercise_factory,
    ):
        user = await user_factory()
        cat = await category_factory()
        await exercise_factory(category_id=cat.id, content={"image": "url.png"})
        await exercise_factory(category_id=cat.id, content={"text": "q"})

        result = await exercise_selector.select_by_content_field(cat.id, user.id, "image", limit=10)

        assert len(result) == 1

    async def test_select_by_content_value(
        self, exercise_selector, user_factory, category_factory, exercise_factory,
    ):
        user = await user_factory()
        cat = await category_factory()
        await exercise_factory(category_id=cat.id, content={"type": "drag"})
        await exercise_factory(category_id=cat.id, content={"type": "input"})

        result = await exercise_selector.select_by_content_value(
            cat.id, user.id, "type", "drag", limit=10,
        )

        assert len(result) == 1

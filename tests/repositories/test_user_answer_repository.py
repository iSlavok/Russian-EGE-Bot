from app.repositories.exercise_filters import answer_eq, answer_ne, content_eq, content_exists


class TestGetAnsweredExerciseIds:
    async def test_empty_returns_empty_set(
        self, user_answer_repository, user_factory, category_factory,
    ):
        user = await user_factory()
        category = await category_factory()

        result = await user_answer_repository.get_answered_exercise_ids(user.id, category.id)

        assert result == set()

    async def test_returns_answered_ids(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        ex1 = await exercise_factory(category_id=category.id)
        ex2 = await exercise_factory(category_id=category.id)
        await exercise_factory(category_id=category.id)  # not answered

        await user_answer_factory(user_id=user.id, exercise_id=ex1.id, category_id=category.id)
        await user_answer_factory(user_id=user.id, exercise_id=ex2.id, category_id=category.id)

        result = await user_answer_repository.get_answered_exercise_ids(user.id, category.id)

        assert result == {ex1.id, ex2.id}

    async def test_deduplicates_multiple_answers(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        exercise = await exercise_factory(category_id=category.id)

        await user_answer_factory(
            user_id=user.id, exercise_id=exercise.id, category_id=category.id, is_correct=True,
        )
        await user_answer_factory(
            user_id=user.id, exercise_id=exercise.id, category_id=category.id, is_correct=False,
        )

        result = await user_answer_repository.get_answered_exercise_ids(user.id, category.id)

        assert result == {exercise.id}

    async def test_filters_by_category(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        cat1 = await category_factory(name="Cat 1")
        cat2 = await category_factory(name="Cat 2")
        ex1 = await exercise_factory(category_id=cat1.id)
        ex2 = await exercise_factory(category_id=cat2.id)

        await user_answer_factory(user_id=user.id, exercise_id=ex1.id, category_id=cat1.id)
        await user_answer_factory(user_id=user.id, exercise_id=ex2.id, category_id=cat2.id)

        result = await user_answer_repository.get_answered_exercise_ids(user.id, cat1.id)

        assert result == {ex1.id}

    async def test_filters_by_user(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user1 = await user_factory(telegram_id=1001)
        user2 = await user_factory(telegram_id=1002)
        category = await category_factory()
        exercise = await exercise_factory(category_id=category.id)

        await user_answer_factory(
            user_id=user1.id, exercise_id=exercise.id, category_id=category.id,
        )

        result = await user_answer_repository.get_answered_exercise_ids(user2.id, category.id)

        assert result == set()

    async def test_many_exercises(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        category = await category_factory()

        expected_ids = set()
        for _ in range(20):
            ex = await exercise_factory(category_id=category.id)
            await user_answer_factory(
                user_id=user.id, exercise_id=ex.id, category_id=category.id,
            )
            expected_ids.add(ex.id)

        result = await user_answer_repository.get_answered_exercise_ids(user.id, category.id)

        assert result == expected_ids


class TestGetExerciseStats:
    async def test_empty_returns_nothing(
        self, user_answer_repository, user_factory, category_factory,
    ):
        user = await user_factory()
        category = await category_factory()

        result = await user_answer_repository.get_exercise_stats(user.id, category.id)

        assert list(result) == []

    async def test_single_correct_answer(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        ex = await exercise_factory(category_id=category.id)

        await user_answer_factory(
            user_id=user.id, exercise_id=ex.id, category_id=category.id,
            is_correct=True, solve_time=15,
        )

        rows = await user_answer_repository.get_exercise_stats(user.id, category.id)

        assert len(rows) == 1
        row = rows[0]
        assert row.exercise_id == ex.id
        assert row.n_correct == 1
        assert row.n_wrong == 0
        assert float(row.avg_solve_time) == 15.0

    async def test_counts_correct_and_wrong(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        ex = await exercise_factory(category_id=category.id)

        await user_answer_factory(
            user_id=user.id, exercise_id=ex.id, category_id=category.id,
            is_correct=True, solve_time=10,
        )
        await user_answer_factory(
            user_id=user.id, exercise_id=ex.id, category_id=category.id,
            is_correct=False, solve_time=20,
        )
        await user_answer_factory(
            user_id=user.id, exercise_id=ex.id, category_id=category.id,
            is_correct=True, solve_time=30,
        )

        rows = await user_answer_repository.get_exercise_stats(user.id, category.id)

        assert len(rows) == 1
        row = rows[0]
        assert row.n_correct == 2
        assert row.n_wrong == 1
        assert float(row.avg_solve_time) == 20.0

    async def test_window_size_limits_answers(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        ex = await exercise_factory(category_id=category.id)

        # 3 старых wrong (solve_time=100)
        for _ in range(3):
            await user_answer_factory(
                user_id=user.id, exercise_id=ex.id, category_id=category.id,
                is_correct=False, solve_time=100,
            )
        # 2 новых correct (solve_time=10) — id больше, значит "новее"
        for _ in range(2):
            await user_answer_factory(
                user_id=user.id, exercise_id=ex.id, category_id=category.id,
                is_correct=True, solve_time=10,
            )

        rows = await user_answer_repository.get_exercise_stats(user.id, category.id, window_size=2)

        assert len(rows) == 1
        row = rows[0]
        # только 2 последних (correct, solve_time=10)
        assert row.n_correct == 2
        assert row.n_wrong == 0
        assert float(row.avg_solve_time) == 10.0

    async def test_multiple_exercises(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        ex1 = await exercise_factory(category_id=category.id)
        ex2 = await exercise_factory(category_id=category.id)

        await user_answer_factory(
            user_id=user.id, exercise_id=ex1.id, category_id=category.id,
            is_correct=True, solve_time=5,
        )
        await user_answer_factory(
            user_id=user.id, exercise_id=ex2.id, category_id=category.id,
            is_correct=False, solve_time=25,
        )

        rows = await user_answer_repository.get_exercise_stats(user.id, category.id)
        stats = {r.exercise_id: r for r in rows}

        assert len(stats) == 2
        assert stats[ex1.id].n_correct == 1
        assert stats[ex2.id].n_wrong == 1

    async def test_filters_by_user(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user1 = await user_factory()
        user2 = await user_factory()
        category = await category_factory()
        ex = await exercise_factory(category_id=category.id)

        await user_answer_factory(
            user_id=user1.id, exercise_id=ex.id, category_id=category.id,
        )

        result = await user_answer_repository.get_exercise_stats(user2.id, category.id)

        assert list(result) == []

    async def test_filters_by_category(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        cat1 = await category_factory(name="Cat 1")
        cat2 = await category_factory(name="Cat 2")
        ex1 = await exercise_factory(category_id=cat1.id)
        ex2 = await exercise_factory(category_id=cat2.id)

        await user_answer_factory(user_id=user.id, exercise_id=ex1.id, category_id=cat1.id)
        await user_answer_factory(user_id=user.id, exercise_id=ex2.id, category_id=cat2.id)

        rows = await user_answer_repository.get_exercise_stats(user.id, cat1.id)

        assert len(rows) == 1
        assert rows[0].exercise_id == ex1.id

    async def test_last_attempt_at_is_most_recent(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        ex = await exercise_factory(category_id=category.id)

        a1 = await user_answer_factory(
            user_id=user.id, exercise_id=ex.id, category_id=category.id,
        )
        a2 = await user_answer_factory(
            user_id=user.id, exercise_id=ex.id, category_id=category.id,
        )

        rows = await user_answer_repository.get_exercise_stats(user.id, category.id)

        assert len(rows) == 1
        assert rows[0].last_attempt_at >= a1.created_at

    async def test_filter_answer_eq(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        ex_yes = await exercise_factory(category_id=category.id, answer="yes")
        ex_no = await exercise_factory(category_id=category.id, answer="no")

        await user_answer_factory(user_id=user.id, exercise_id=ex_yes.id, category_id=category.id)
        await user_answer_factory(user_id=user.id, exercise_id=ex_no.id, category_id=category.id)

        rows = await user_answer_repository.get_exercise_stats(
            user.id, category.id, filters=[answer_eq("yes")],
        )

        assert len(rows) == 1
        assert rows[0].exercise_id == ex_yes.id

    async def test_filter_answer_ne(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        ex_yes = await exercise_factory(category_id=category.id, answer="yes")
        ex_no = await exercise_factory(category_id=category.id, answer="no")

        await user_answer_factory(user_id=user.id, exercise_id=ex_yes.id, category_id=category.id)
        await user_answer_factory(user_id=user.id, exercise_id=ex_no.id, category_id=category.id)

        rows = await user_answer_repository.get_exercise_stats(
            user.id, category.id, filters=[answer_ne("yes")],
        )

        assert len(rows) == 1
        assert rows[0].exercise_id == ex_no.id

    async def test_filter_content_exists(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        ex_with = await exercise_factory(
            category_id=category.id, content={"image": "url.png", "text": "q"},
        )
        ex_without = await exercise_factory(
            category_id=category.id, content={"text": "q"},
        )

        await user_answer_factory(user_id=user.id, exercise_id=ex_with.id, category_id=category.id)
        await user_answer_factory(user_id=user.id, exercise_id=ex_without.id, category_id=category.id)

        rows = await user_answer_repository.get_exercise_stats(
            user.id, category.id, filters=[content_exists("image")],
        )

        assert len(rows) == 1
        assert rows[0].exercise_id == ex_with.id

    async def test_filter_content_eq(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        ex_drag = await exercise_factory(
            category_id=category.id, content={"type": "drag", "text": "q"},
        )
        ex_input = await exercise_factory(
            category_id=category.id, content={"type": "input", "text": "q"},
        )

        await user_answer_factory(user_id=user.id, exercise_id=ex_drag.id, category_id=category.id)
        await user_answer_factory(user_id=user.id, exercise_id=ex_input.id, category_id=category.id)

        rows = await user_answer_repository.get_exercise_stats(
            user.id, category.id, filters=[content_eq("type", "drag")],
        )

        assert len(rows) == 1
        assert rows[0].exercise_id == ex_drag.id

    async def test_filter_no_filters_returns_all(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        ex1 = await exercise_factory(category_id=category.id, answer="a")
        ex2 = await exercise_factory(category_id=category.id, answer="b")

        await user_answer_factory(user_id=user.id, exercise_id=ex1.id, category_id=category.id)
        await user_answer_factory(user_id=user.id, exercise_id=ex2.id, category_id=category.id)

        rows = await user_answer_repository.get_exercise_stats(
            user.id, category.id, filters=None,
        )

        assert len(rows) == 2


class TestGetGroupStats:
    async def test_empty_returns_nothing(
        self, user_answer_repository, user_factory, category_factory,
    ):
        user = await user_factory()
        category = await category_factory()

        result = await user_answer_repository.get_group_stats(user.id, category.id)

        assert list(result) == []

    async def test_cross_category_aggregation(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        cat1 = await category_factory(name="Cat 1")
        cat2 = await category_factory(name="Cat 2")
        g1 = "11111111-1111-1111-1111-111111111111"

        ex_cat1 = await exercise_factory(category_id=cat1.id, group_id=g1)
        ex_cat2 = await exercise_factory(category_id=cat2.id, group_id=g1)

        await user_answer_factory(
            user_id=user.id, exercise_id=ex_cat1.id, category_id=cat1.id,
            is_correct=True, solve_time=10,
        )
        await user_answer_factory(
            user_id=user.id, exercise_id=ex_cat2.id, category_id=cat2.id,
            is_correct=False, solve_time=20,
        )

        rows = await user_answer_repository.get_group_stats(user.id, cat1.id)

        assert len(rows) == 1
        row = rows[0]
        assert row.n_correct == 1
        assert row.n_wrong == 1

    async def test_ignores_null_group(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        ex_null = await exercise_factory(category_id=category.id, group_id=None)

        await user_answer_factory(
            user_id=user.id, exercise_id=ex_null.id, category_id=category.id,
        )

        rows = await user_answer_repository.get_group_stats(user.id, category.id)

        assert list(rows) == []

    async def test_window_size(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        g1 = "11111111-1111-1111-1111-111111111111"
        ex = await exercise_factory(category_id=category.id, group_id=g1)

        for _ in range(3):
            await user_answer_factory(
                user_id=user.id, exercise_id=ex.id, category_id=category.id,
                is_correct=False, solve_time=100,
            )
        for _ in range(2):
            await user_answer_factory(
                user_id=user.id, exercise_id=ex.id, category_id=category.id,
                is_correct=True, solve_time=10,
            )

        rows = await user_answer_repository.get_group_stats(
            user.id, category.id, window_size=2,
        )

        assert len(rows) == 1
        assert rows[0].n_correct == 2
        assert rows[0].n_wrong == 0

    async def test_filters_by_user(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user1 = await user_factory()
        user2 = await user_factory()
        category = await category_factory()
        g1 = "11111111-1111-1111-1111-111111111111"
        ex = await exercise_factory(category_id=category.id, group_id=g1)

        await user_answer_factory(
            user_id=user1.id, exercise_id=ex.id, category_id=category.id,
        )

        rows = await user_answer_repository.get_group_stats(user2.id, category.id)

        assert list(rows) == []

    async def test_multiple_groups(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        g1 = "11111111-1111-1111-1111-111111111111"
        g2 = "22222222-2222-2222-2222-222222222222"
        ex1 = await exercise_factory(category_id=category.id, group_id=g1)
        ex2 = await exercise_factory(category_id=category.id, group_id=g2)

        await user_answer_factory(
            user_id=user.id, exercise_id=ex1.id, category_id=category.id,
            is_correct=True,
        )
        await user_answer_factory(
            user_id=user.id, exercise_id=ex2.id, category_id=category.id,
            is_correct=False,
        )

        rows = await user_answer_repository.get_group_stats(user.id, category.id)

        assert len(rows) == 2

    async def test_with_filters(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        g1 = "11111111-1111-1111-1111-111111111111"
        g2 = "22222222-2222-2222-2222-222222222222"
        ex1 = await exercise_factory(category_id=category.id, group_id=g1, answer="yes")
        ex2 = await exercise_factory(category_id=category.id, group_id=g2, answer="no")

        await user_answer_factory(
            user_id=user.id, exercise_id=ex1.id, category_id=category.id,
        )
        await user_answer_factory(
            user_id=user.id, exercise_id=ex2.id, category_id=category.id,
        )

        rows = await user_answer_repository.get_group_stats(
            user.id, category.id, filters=[answer_eq("yes")],
        )

        assert len(rows) == 1

    async def test_only_drill_answered_aggregates_for_exam(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        """Ответили только drill (cat_drill), запрашиваем stats для exam (cat_exam).

        Реальный сценарий: drill cat 53, exam cat 54, общий group_id.
        """
        user = await user_factory()
        cat_drill = await category_factory(name="Drill")
        cat_exam = await category_factory(name="Exam")
        g1 = "11111111-1111-1111-1111-111111111111"

        ex_drill = await exercise_factory(category_id=cat_drill.id, group_id=g1)
        await exercise_factory(category_id=cat_exam.id, group_id=g1)  # exam exercise, not answered

        await user_answer_factory(
            user_id=user.id, exercise_id=ex_drill.id, category_id=cat_drill.id,
            is_correct=False, solve_time=30,
        )

        # target = cat_exam — должен подхватить drill-ответ
        rows = await user_answer_repository.get_group_stats(user.id, cat_exam.id)

        assert len(rows) == 1
        row = rows[0]
        assert row.n_wrong == 1
        assert row.n_correct == 0
        assert float(row.avg_solve_time) == 30.0

    async def test_cross_category_avg_solve_time_and_last_attempt(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        """avg_solve_time и last_attempt_at агрегируются кросс-категорийно."""
        user = await user_factory()
        cat1 = await category_factory(name="Cat 1")
        cat2 = await category_factory(name="Cat 2")
        g1 = "11111111-1111-1111-1111-111111111111"

        ex1 = await exercise_factory(category_id=cat1.id, group_id=g1)
        ex2 = await exercise_factory(category_id=cat2.id, group_id=g1)

        a1 = await user_answer_factory(
            user_id=user.id, exercise_id=ex1.id, category_id=cat1.id,
            is_correct=True, solve_time=10,
        )
        a2 = await user_answer_factory(
            user_id=user.id, exercise_id=ex2.id, category_id=cat2.id,
            is_correct=True, solve_time=30,
        )

        rows = await user_answer_repository.get_group_stats(user.id, cat1.id)

        assert len(rows) == 1
        row = rows[0]
        assert float(row.avg_solve_time) == 20.0  # (10 + 30) / 2
        assert row.last_attempt_at >= a1.created_at
        assert row.last_attempt_at >= a2.created_at


class TestGetAnswerGroupStats:
    async def test_empty_returns_nothing(
        self, user_answer_repository, user_factory, category_factory,
    ):
        user = await user_factory()
        category = await category_factory()

        result = await user_answer_repository.get_answer_group_stats(
            user.id, category.id, min_group_size=1,
        )

        assert list(result) == []

    async def test_returns_eligible_answers(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        for _ in range(3):
            await exercise_factory(category_id=category.id, answer="A")
        await exercise_factory(category_id=category.id, answer="B")

        rows = await user_answer_repository.get_answer_group_stats(
            user.id, category.id, min_group_size=2,
        )

        answers = {r.answer for r in rows}
        assert "A" in answers
        assert "B" not in answers

    async def test_counts_total_and_unseen(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        ex1 = await exercise_factory(category_id=category.id, answer="A")
        await exercise_factory(category_id=category.id, answer="A")
        await exercise_factory(category_id=category.id, answer="A")

        await user_answer_factory(
            user_id=user.id, exercise_id=ex1.id, category_id=category.id,
        )

        rows = await user_answer_repository.get_answer_group_stats(
            user.id, category.id, min_group_size=1,
        )

        row = [r for r in rows if r.answer == "A"][0]
        assert int(row.total) == 3
        assert int(row.unseen_count) == 2

    async def test_aggregates_user_stats(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        ex1 = await exercise_factory(category_id=category.id, answer="A")
        ex2 = await exercise_factory(category_id=category.id, answer="A")

        await user_answer_factory(
            user_id=user.id, exercise_id=ex1.id, category_id=category.id,
            is_correct=True, solve_time=10,
        )
        await user_answer_factory(
            user_id=user.id, exercise_id=ex2.id, category_id=category.id,
            is_correct=False, solve_time=20,
        )

        rows = await user_answer_repository.get_answer_group_stats(
            user.id, category.id, min_group_size=1,
        )

        row = [r for r in rows if r.answer == "A"][0]
        assert int(row.n_correct) == 1
        assert int(row.n_wrong) == 1

    async def test_no_answers_all_unseen(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        for _ in range(3):
            await exercise_factory(category_id=category.id, answer="X")

        rows = await user_answer_repository.get_answer_group_stats(
            user.id, category.id, min_group_size=1,
        )

        row = [r for r in rows if r.answer == "X"][0]
        assert int(row.total) == 3
        assert int(row.unseen_count) == 3
        assert int(row.n_correct) == 0
        assert int(row.n_wrong) == 0

    async def test_filters_by_user(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user1 = await user_factory()
        user2 = await user_factory()
        category = await category_factory()
        ex = await exercise_factory(category_id=category.id, answer="A")
        await exercise_factory(category_id=category.id, answer="A")

        await user_answer_factory(
            user_id=user1.id, exercise_id=ex.id, category_id=category.id,
            is_correct=True,
        )

        rows = await user_answer_repository.get_answer_group_stats(
            user2.id, category.id, min_group_size=1,
        )

        row = [r for r in rows if r.answer == "A"][0]
        assert int(row.unseen_count) == 2
        assert int(row.n_correct) == 0

    async def test_excludes_inactive(
        self,
        user_answer_repository,
        user_factory,
        category_factory,
        exercise_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        await exercise_factory(category_id=category.id, answer="A", is_active=True)
        await exercise_factory(category_id=category.id, answer="A", is_active=False)

        rows = await user_answer_repository.get_answer_group_stats(
            user.id, category.id, min_group_size=1,
        )

        row = [r for r in rows if r.answer == "A"][0]
        assert int(row.total) == 1

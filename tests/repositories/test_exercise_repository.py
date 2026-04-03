from app.repositories.exercise_filters import answer_eq, answer_ne, content_eq, content_exists


class TestGetRandomUnseen:
    async def test_returns_unseen_exercises(
        self, exercise_repository, user_factory, category_factory, exercise_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        ex1 = await exercise_factory(category_id=category.id)
        ex2 = await exercise_factory(category_id=category.id)

        result = await exercise_repository.get_random_unseen(category.id, user.id, limit=10)

        result_ids = {e.id for e in result}
        assert result_ids == {ex1.id, ex2.id}

    async def test_excludes_answered(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        seen = await exercise_factory(category_id=category.id)
        unseen = await exercise_factory(category_id=category.id)

        await user_answer_factory(user_id=user.id, exercise_id=seen.id, category_id=category.id)

        result = await exercise_repository.get_random_unseen(category.id, user.id, limit=10)

        result_ids = {e.id for e in result}
        assert result_ids == {unseen.id}

    async def test_empty_when_all_answered(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        ex = await exercise_factory(category_id=category.id)

        await user_answer_factory(user_id=user.id, exercise_id=ex.id, category_id=category.id)

        result = await exercise_repository.get_random_unseen(category.id, user.id, limit=10)

        assert list(result) == []

    async def test_excludes_inactive(
        self, exercise_repository, user_factory, category_factory, exercise_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        await exercise_factory(category_id=category.id, is_active=False)
        active = await exercise_factory(category_id=category.id, is_active=True)

        result = await exercise_repository.get_random_unseen(category.id, user.id, limit=10)

        result_ids = {e.id for e in result}
        assert result_ids == {active.id}

    async def test_respects_limit(
        self, exercise_repository, user_factory, category_factory, exercise_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        for _ in range(5):
            await exercise_factory(category_id=category.id)

        result = await exercise_repository.get_random_unseen(category.id, user.id, limit=2)

        assert len(result) == 2

    async def test_filters_by_category(
        self, exercise_repository, user_factory, category_factory, exercise_factory,
    ):
        user = await user_factory()
        cat1 = await category_factory(name="Cat 1")
        cat2 = await category_factory(name="Cat 2")
        ex1 = await exercise_factory(category_id=cat1.id)
        await exercise_factory(category_id=cat2.id)

        result = await exercise_repository.get_random_unseen(cat1.id, user.id, limit=10)

        result_ids = {e.id for e in result}
        assert result_ids == {ex1.id}

    async def test_other_user_answers_dont_affect(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user1 = await user_factory()
        user2 = await user_factory()
        category = await category_factory()
        ex = await exercise_factory(category_id=category.id)

        await user_answer_factory(user_id=user1.id, exercise_id=ex.id, category_id=category.id)

        result = await exercise_repository.get_random_unseen(category.id, user2.id, limit=10)

        assert len(result) == 1
        assert result[0].id == ex.id

    async def test_empty_category(
        self, exercise_repository, user_factory, category_factory,
    ):
        user = await user_factory()
        category = await category_factory()

        result = await exercise_repository.get_random_unseen(category.id, user.id, limit=10)

        assert list(result) == []

    async def test_filter_answer_eq(
        self, exercise_repository, user_factory, category_factory, exercise_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        match = await exercise_factory(category_id=category.id, answer="yes")
        await exercise_factory(category_id=category.id, answer="no")

        result = await exercise_repository.get_random_unseen(
            category.id, user.id, limit=10, filters=[answer_eq("yes")],
        )

        assert {e.id for e in result} == {match.id}

    async def test_filter_answer_ne(
        self, exercise_repository, user_factory, category_factory, exercise_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        await exercise_factory(category_id=category.id, answer="exclude_me")
        keep = await exercise_factory(category_id=category.id, answer="keep")

        result = await exercise_repository.get_random_unseen(
            category.id, user.id, limit=10, filters=[answer_ne("exclude_me")],
        )

        assert {e.id for e in result} == {keep.id}

    async def test_filter_content_exists(
        self, exercise_repository, user_factory, category_factory, exercise_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        with_field = await exercise_factory(
            category_id=category.id, content={"image": "url.png", "text": "q"},
        )
        await exercise_factory(category_id=category.id, content={"text": "q"})

        result = await exercise_repository.get_random_unseen(
            category.id, user.id, limit=10, filters=[content_exists("image")],
        )

        assert {e.id for e in result} == {with_field.id}

    async def test_filter_content_eq(
        self, exercise_repository, user_factory, category_factory, exercise_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        match = await exercise_factory(
            category_id=category.id, content={"type": "drag", "text": "q"},
        )
        await exercise_factory(
            category_id=category.id, content={"type": "input", "text": "q"},
        )

        result = await exercise_repository.get_random_unseen(
            category.id, user.id, limit=10, filters=[content_eq("type", "drag")],
        )

        assert {e.id for e in result} == {match.id}

    async def test_filter_combined_with_unseen(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        seen_match = await exercise_factory(category_id=category.id, answer="yes")
        unseen_match = await exercise_factory(category_id=category.id, answer="yes")
        await exercise_factory(category_id=category.id, answer="no")

        await user_answer_factory(
            user_id=user.id, exercise_id=seen_match.id, category_id=category.id,
        )

        result = await exercise_repository.get_random_unseen(
            category.id, user.id, limit=10, filters=[answer_eq("yes")],
        )

        assert {e.id for e in result} == {unseen_match.id}

    async def test_distinct_on_answer_returns_one_per_answer(
        self, exercise_repository, user_factory, category_factory, exercise_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        await exercise_factory(category_id=category.id, answer="A")
        await exercise_factory(category_id=category.id, answer="A")
        await exercise_factory(category_id=category.id, answer="B")
        await exercise_factory(category_id=category.id, answer="B")
        await exercise_factory(category_id=category.id, answer="C")

        result = await exercise_repository.get_random_unseen(
            category.id, user.id, limit=10, distinct_on_answer=True,
        )

        answers = [e.answer for e in result]
        assert len(answers) == 3
        assert set(answers) == {"A", "B", "C"}

    async def test_distinct_on_answer_excludes_seen(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        seen = await exercise_factory(category_id=category.id, answer="A")
        unseen_a = await exercise_factory(category_id=category.id, answer="A")
        unseen_b = await exercise_factory(category_id=category.id, answer="B")

        await user_answer_factory(user_id=user.id, exercise_id=seen.id, category_id=category.id)

        result = await exercise_repository.get_random_unseen(
            category.id, user.id, limit=10, distinct_on_answer=True,
        )

        result_ids = {e.id for e in result}
        assert unseen_a.id in result_ids
        assert unseen_b.id in result_ids
        assert seen.id not in result_ids
        assert len(result) == 2

    async def test_distinct_on_answer_respects_limit(
        self, exercise_repository, user_factory, category_factory, exercise_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        for letter in "ABCDE":
            await exercise_factory(category_id=category.id, answer=letter)

        result = await exercise_repository.get_random_unseen(
            category.id, user.id, limit=2, distinct_on_answer=True,
        )

        assert len(result) == 2
        assert len({e.answer for e in result}) == 2


class TestGetRandomDistinctGroupFiller:
    async def test_returns_distinct_groups(
        self, exercise_repository, category_factory, exercise_factory,
    ):
        category = await category_factory()
        g1 = "11111111-1111-1111-1111-111111111111"
        g2 = "22222222-2222-2222-2222-222222222222"
        await exercise_factory(category_id=category.id, group_id=g1)
        await exercise_factory(category_id=category.id, group_id=g1)
        await exercise_factory(category_id=category.id, group_id=g2)

        result = await exercise_repository.get_random_distinct_group_filler(
            category.id, limit=10,
        )

        group_ids = {e.group_id for e in result}
        assert len(group_ids) == 2

    async def test_null_group_treated_as_distinct(
        self, exercise_repository, category_factory, exercise_factory,
    ):
        category = await category_factory()
        await exercise_factory(category_id=category.id, group_id=None)
        await exercise_factory(category_id=category.id, group_id=None)

        result = await exercise_repository.get_random_distinct_group_filler(
            category.id, limit=10,
        )

        assert len(result) == 2

    async def test_exclude_ids(
        self, exercise_repository, category_factory, exercise_factory,
    ):
        category = await category_factory()
        ex1 = await exercise_factory(category_id=category.id)
        await exercise_factory(category_id=category.id)

        result = await exercise_repository.get_random_distinct_group_filler(
            category.id, limit=10, exclude_ids=[ex1.id],
        )

        result_ids = {e.id for e in result}
        assert ex1.id not in result_ids

    async def test_exclude_group_ids(
        self, exercise_repository, category_factory, exercise_factory,
    ):
        import uuid
        category = await category_factory()
        g1 = "11111111-1111-1111-1111-111111111111"
        g2 = "22222222-2222-2222-2222-222222222222"
        await exercise_factory(category_id=category.id, group_id=g1)
        ex2 = await exercise_factory(category_id=category.id, group_id=g2)

        result = await exercise_repository.get_random_distinct_group_filler(
            category.id, limit=10, exclude_group_ids=[uuid.UUID(g1)],
        )

        result_ids = {e.id for e in result}
        assert ex2.id in result_ids
        assert len(result) == 1

    async def test_respects_limit(
        self, exercise_repository, category_factory, exercise_factory,
    ):
        category = await category_factory()
        for _ in range(5):
            await exercise_factory(category_id=category.id)

        result = await exercise_repository.get_random_distinct_group_filler(
            category.id, limit=2,
        )

        assert len(result) == 2


class TestGetRandomUnseenByGroup:
    async def test_returns_unseen_groups(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        g1 = "11111111-1111-1111-1111-111111111111"
        g2 = "22222222-2222-2222-2222-222222222222"
        await exercise_factory(category_id=category.id, group_id=g1)
        await exercise_factory(category_id=category.id, group_id=g1)
        await exercise_factory(category_id=category.id, group_id=g2)

        result = await exercise_repository.get_random_unseen_by_group(
            category.id, user.id, limit=10,
        )

        group_ids = {e.group_id for e in result}
        assert len(group_ids) == 2

    async def test_excludes_seen_group_cross_category(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        cat1 = await category_factory(name="Cat A")
        cat2 = await category_factory(name="Cat B")
        g1 = "11111111-1111-1111-1111-111111111111"
        g2 = "22222222-2222-2222-2222-222222222222"

        ex_cat2_g1 = await exercise_factory(category_id=cat2.id, group_id=g1)
        await exercise_factory(category_id=cat1.id, group_id=g1)
        await exercise_factory(category_id=cat1.id, group_id=g2)

        await user_answer_factory(
            user_id=user.id, exercise_id=ex_cat2_g1.id, category_id=cat2.id,
        )

        result = await exercise_repository.get_random_unseen_by_group(
            cat1.id, user.id, limit=10,
        )

        group_ids = {e.group_id for e in result}
        assert g1 not in {str(gid) for gid in group_ids}

    async def test_null_group_falls_back_to_exercise_check(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        seen_null = await exercise_factory(category_id=category.id, group_id=None)
        unseen_null = await exercise_factory(category_id=category.id, group_id=None)

        await user_answer_factory(
            user_id=user.id, exercise_id=seen_null.id, category_id=category.id,
        )

        result = await exercise_repository.get_random_unseen_by_group(
            category.id, user.id, limit=10,
        )

        result_ids = {e.id for e in result}
        assert unseen_null.id in result_ids
        assert seen_null.id not in result_ids

    async def test_respects_limit(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        for i in range(5):
            gid = f"{i+1:08d}-0000-0000-0000-000000000000"
            await exercise_factory(category_id=category.id, group_id=gid)

        result = await exercise_repository.get_random_unseen_by_group(
            category.id, user.id, limit=2,
        )

        assert len(result) == 2

    async def test_excludes_inactive(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        g1 = "11111111-1111-1111-1111-111111111111"
        await exercise_factory(category_id=category.id, group_id=g1, is_active=False)
        active = await exercise_factory(category_id=category.id, group_id=None)

        result = await exercise_repository.get_random_unseen_by_group(
            category.id, user.id, limit=10,
        )

        result_ids = {e.id for e in result}
        assert active.id in result_ids
        assert len(result) == 1

    async def test_with_filters(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        g1 = "11111111-1111-1111-1111-111111111111"
        g2 = "22222222-2222-2222-2222-222222222222"
        await exercise_factory(category_id=category.id, group_id=g1, answer="yes")
        await exercise_factory(category_id=category.id, group_id=g2, answer="no")

        result = await exercise_repository.get_random_unseen_by_group(
            category.id, user.id, limit=10, filters=[answer_eq("yes")],
        )

        assert len(result) == 1
        assert result[0].answer == "yes"

    async def test_all_groups_seen_returns_empty(
        self,
        exercise_repository,
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

        await user_answer_factory(user_id=user.id, exercise_id=ex1.id, category_id=category.id)
        await user_answer_factory(user_id=user.id, exercise_id=ex2.id, category_id=category.id)

        result = await exercise_repository.get_random_unseen_by_group(
            category.id, user.id, limit=10,
        )

        assert list(result) == []

    async def test_other_user_answers_dont_affect(
        self,
        exercise_repository,
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

        await user_answer_factory(user_id=user1.id, exercise_id=ex.id, category_id=category.id)

        result = await exercise_repository.get_random_unseen_by_group(
            category.id, user2.id, limit=10,
        )

        assert len(result) == 1
        assert result[0].id == ex.id

    async def test_mixed_null_and_grouped(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        """NULL group и non-NULL group в одном запросе, частично seen."""
        user = await user_factory()
        category = await category_factory()
        g1 = "11111111-1111-1111-1111-111111111111"
        g2 = "22222222-2222-2222-2222-222222222222"

        ex_g1 = await exercise_factory(category_id=category.id, group_id=g1)
        unseen_g2 = await exercise_factory(category_id=category.id, group_id=g2)
        seen_null = await exercise_factory(category_id=category.id, group_id=None)
        unseen_null = await exercise_factory(category_id=category.id, group_id=None)

        # g1 seen, null_seen seen
        await user_answer_factory(user_id=user.id, exercise_id=ex_g1.id, category_id=category.id)
        await user_answer_factory(user_id=user.id, exercise_id=seen_null.id, category_id=category.id)

        result = await exercise_repository.get_random_unseen_by_group(
            category.id, user.id, limit=10,
        )

        result_ids = {e.id for e in result}
        assert unseen_g2.id in result_ids
        assert unseen_null.id in result_ids
        assert ex_g1.id not in result_ids
        assert seen_null.id not in result_ids

    async def test_distinct_one_per_group(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
    ):
        """3 exercise в одной unseen группе → возвращается ровно 1."""
        user = await user_factory()
        category = await category_factory()
        g1 = "11111111-1111-1111-1111-111111111111"
        await exercise_factory(category_id=category.id, group_id=g1)
        await exercise_factory(category_id=category.id, group_id=g1)
        await exercise_factory(category_id=category.id, group_id=g1)

        result = await exercise_repository.get_random_unseen_by_group(
            category.id, user.id, limit=10,
        )

        assert len(result) == 1


class TestGetRandomByGroupIds:
    async def test_returns_one_per_group(
        self, exercise_repository, category_factory, exercise_factory,
    ):
        import uuid
        category = await category_factory()
        g1 = "11111111-1111-1111-1111-111111111111"
        g2 = "22222222-2222-2222-2222-222222222222"
        await exercise_factory(category_id=category.id, group_id=g1)
        await exercise_factory(category_id=category.id, group_id=g1)
        await exercise_factory(category_id=category.id, group_id=g2)

        result = await exercise_repository.get_random_by_group_ids(
            category.id, [uuid.UUID(g1), uuid.UUID(g2)],
        )

        group_ids = [e.group_id for e in result]
        assert len(result) == 2
        assert len(set(group_ids)) == 2

    async def test_empty_group_ids_returns_empty(
        self, exercise_repository, category_factory,
    ):
        category = await category_factory()

        result = await exercise_repository.get_random_by_group_ids(
            category.id, [],
        )

        assert list(result) == []

    async def test_exclude_ids(
        self, exercise_repository, category_factory, exercise_factory,
    ):
        import uuid
        category = await category_factory()
        g1 = "11111111-1111-1111-1111-111111111111"
        ex1 = await exercise_factory(category_id=category.id, group_id=g1)
        ex2 = await exercise_factory(category_id=category.id, group_id=g1)

        result = await exercise_repository.get_random_by_group_ids(
            category.id, [uuid.UUID(g1)], exclude_ids={ex1.id},
        )

        assert len(result) == 1
        assert result[0].id == ex2.id

    async def test_excludes_inactive(
        self, exercise_repository, category_factory, exercise_factory,
    ):
        import uuid
        category = await category_factory()
        g1 = "11111111-1111-1111-1111-111111111111"
        await exercise_factory(category_id=category.id, group_id=g1, is_active=False)

        result = await exercise_repository.get_random_by_group_ids(
            category.id, [uuid.UUID(g1)],
        )

        assert list(result) == []

    async def test_with_filters(
        self, exercise_repository, category_factory, exercise_factory,
    ):
        import uuid
        category = await category_factory()
        g1 = "11111111-1111-1111-1111-111111111111"
        g2 = "22222222-2222-2222-2222-222222222222"
        await exercise_factory(category_id=category.id, group_id=g1, answer="yes")
        await exercise_factory(category_id=category.id, group_id=g2, answer="no")

        result = await exercise_repository.get_random_by_group_ids(
            category.id, [uuid.UUID(g1), uuid.UUID(g2)], filters=[answer_eq("yes")],
        )

        assert len(result) == 1
        assert result[0].answer == "yes"

    async def test_filters_by_category(
        self, exercise_repository, category_factory, exercise_factory,
    ):
        import uuid
        cat1 = await category_factory(name="Cat 1")
        cat2 = await category_factory(name="Cat 2")
        g1 = "11111111-1111-1111-1111-111111111111"
        await exercise_factory(category_id=cat1.id, group_id=g1)
        await exercise_factory(category_id=cat2.id, group_id=g1)

        result = await exercise_repository.get_random_by_group_ids(
            cat1.id, [uuid.UUID(g1)],
        )

        assert len(result) == 1
        assert result[0].category_id == cat1.id


class TestGetExercisesByAnswersUnseenFirst:
    async def test_returns_exercises_for_given_answers(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        ex_a = await exercise_factory(category_id=category.id, answer="A")
        ex_b = await exercise_factory(category_id=category.id, answer="B")
        await exercise_factory(category_id=category.id, answer="C")

        result = await exercise_repository.get_exercises_by_answers_unseen_first(
            category.id, user.id, answers={"A", "B"}, per_answer_limit=5,
        )

        result_ids = {e.id for e in result}
        assert ex_a.id in result_ids
        assert ex_b.id in result_ids

    async def test_unseen_prioritized(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        seen = await exercise_factory(category_id=category.id, answer="A")
        unseen = await exercise_factory(category_id=category.id, answer="A")

        await user_answer_factory(
            user_id=user.id, exercise_id=seen.id, category_id=category.id,
        )

        result = await exercise_repository.get_exercises_by_answers_unseen_first(
            category.id, user.id, answers={"A"}, per_answer_limit=1,
        )

        assert len(result) == 1
        assert result[0].id == unseen.id

    async def test_per_answer_limit(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        for _ in range(5):
            await exercise_factory(category_id=category.id, answer="A")

        result = await exercise_repository.get_exercises_by_answers_unseen_first(
            category.id, user.id, answers={"A"}, per_answer_limit=2,
        )

        assert len(result) == 2

    async def test_exclude_ids(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        ex1 = await exercise_factory(category_id=category.id, answer="A")
        ex2 = await exercise_factory(category_id=category.id, answer="A")

        result = await exercise_repository.get_exercises_by_answers_unseen_first(
            category.id, user.id, answers={"A"}, per_answer_limit=5,
            exclude_ids={ex1.id},
        )

        result_ids = {e.id for e in result}
        assert ex1.id not in result_ids
        assert ex2.id in result_ids

    async def test_empty_answers_returns_empty(
        self, exercise_repository, user_factory, category_factory,
    ):
        user = await user_factory()
        category = await category_factory()

        result = await exercise_repository.get_exercises_by_answers_unseen_first(
            category.id, user.id, answers=set(), per_answer_limit=5,
        )

        assert list(result) == []

    async def test_excludes_inactive(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        await exercise_factory(category_id=category.id, answer="A", is_active=False)
        active = await exercise_factory(category_id=category.id, answer="A")

        result = await exercise_repository.get_exercises_by_answers_unseen_first(
            category.id, user.id, answers={"A"}, per_answer_limit=5,
        )

        assert len(result) == 1
        assert result[0].id == active.id

    async def test_multiple_answers_independent_limits(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
    ):
        user = await user_factory()
        category = await category_factory()
        for _ in range(4):
            await exercise_factory(category_id=category.id, answer="A")
        for _ in range(4):
            await exercise_factory(category_id=category.id, answer="B")

        result = await exercise_repository.get_exercises_by_answers_unseen_first(
            category.id, user.id, answers={"A", "B"}, per_answer_limit=2,
        )

        by_answer = {}
        for e in result:
            by_answer.setdefault(e.answer, []).append(e)

        assert len(by_answer["A"]) == 2
        assert len(by_answer["B"]) == 2


class TestGetByIds:
    async def test_returns_matching(
        self, exercise_repository, category_factory, exercise_factory,
    ):
        category = await category_factory()
        ex1 = await exercise_factory(category_id=category.id)
        ex2 = await exercise_factory(category_id=category.id)
        ex3 = await exercise_factory(category_id=category.id)

        result = await exercise_repository.get_by_ids([ex1.id, ex3.id])

        result_ids = {e.id for e in result}
        assert result_ids == {ex1.id, ex3.id}

    async def test_empty_ids_returns_empty(self, exercise_repository):
        result = await exercise_repository.get_by_ids([])

        assert list(result) == []

    async def test_nonexistent_ids_ignored(
        self, exercise_repository, category_factory, exercise_factory,
    ):
        category = await category_factory()
        ex = await exercise_factory(category_id=category.id)

        result = await exercise_repository.get_by_ids([ex.id, 999999])

        result_ids = {e.id for e in result}
        assert result_ids == {ex.id}


def _make_exam22_content(other_devices: list[str] | None = None) -> dict:
    """Хелпер для создания content упражнения задания 22."""
    return {
        "sentence": "Тестовое предложение.",
        "distractor_devices": ["d1", "d2", "d3", "d4"],
        "other_devices": other_devices or [],
    }


class TestGetExam22Exercises:
    async def test_returns_5_compatible_exercises(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
    ):
        """5 упражнений с непересекающимися ответами и без other_devices — должно найти набор из 5."""
        user = await user_factory()
        category = await category_factory()

        devices = ["metaphor", "epithet", "anaphora", "litotes", "hyperbole",
                    "irony", "oxymoron", "gradation", "inversion", "parallelism"]
        for i in range(10):
            await exercise_factory(
                category_id=category.id,
                answer=devices[i],
                content=_make_exam22_content(),
            )

        result = await exercise_repository.get_exam_22_exercises(category.id, user.id)

        assert len(result) == 5
        answers = [ex.answer for ex in result]
        assert len(set(answers)) == 5

    async def test_empty_when_not_enough_exercises(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
    ):
        """Менее 5 упражнений — не удастся построить путь глубины 5."""
        user = await user_factory()
        category = await category_factory()

        for device in ["metaphor", "epithet", "anaphora"]:
            await exercise_factory(
                category_id=category.id,
                answer=device,
                content=_make_exam22_content(),
            )

        result = await exercise_repository.get_exam_22_exercises(category.id, user.id)

        assert len(result) < 5

    async def test_answers_dont_overlap_with_present(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
    ):
        """Ответы выбранных упражнений не пересекаются с present-устройствами других."""
        user = await user_factory()
        category = await category_factory()

        # Создаём 8 упражнений с уникальными answer и непересекающимися other_devices
        configs = [
            ("d_a", ["o_a1"]),
            ("d_b", ["o_b1"]),
            ("d_c", ["o_c1"]),
            ("d_d", ["o_d1"]),
            ("d_e", ["o_e1"]),
            ("d_f", ["o_f1"]),
            ("d_g", ["o_g1"]),
            ("d_h", ["o_h1"]),
        ]
        for answer, others in configs:
            await exercise_factory(
                category_id=category.id,
                answer=answer,
                content=_make_exam22_content(others),
            )

        result = await exercise_repository.get_exam_22_exercises(category.id, user.id)

        assert len(result) == 5

        # Проверяем совместимость: a_arr одного не пересекается с p_arr другого
        for i, ex_i in enumerate(result):
            a_i = set(ex_i.answer.split(";"))
            for j, ex_j in enumerate(result):
                if i == j:
                    continue
                p_j = set(ex_j.answer.split(";"))
                p_j.update(ex_j.content.get("other_devices", []))
                assert a_i.isdisjoint(p_j), (
                    f"answer {a_i} of ex[{i}] overlaps with present {p_j} of ex[{j}]"
                )

    async def test_distinct_present_count_within_limit(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
    ):
        """Суммарное число distinct present-устройств <= 19."""
        user = await user_factory()
        category = await category_factory()

        for i in range(10):
            await exercise_factory(
                category_id=category.id,
                answer=f"dev_{i}",
                content=_make_exam22_content([f"other_{i}"]),
            )

        result = await exercise_repository.get_exam_22_exercises(category.id, user.id)

        if len(result) == 5:
            all_present: set[str] = set()
            for ex in result:
                all_present.update(ex.answer.split(";"))
                all_present.update(ex.content.get("other_devices", []))
            assert len(all_present) <= 19

    async def test_excludes_inactive(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
    ):
        user = await user_factory()
        category = await category_factory()

        # 5 inactive
        for i in range(5):
            await exercise_factory(
                category_id=category.id,
                answer=f"inactive_{i}",
                content=_make_exam22_content(),
                is_active=False,
            )
        # only 3 active — not enough for depth=5
        for i in range(3):
            await exercise_factory(
                category_id=category.id,
                answer=f"active_{i}",
                content=_make_exam22_content(),
            )

        result = await exercise_repository.get_exam_22_exercises(category.id, user.id)

        assert len(result) < 5

    async def test_prioritizes_unseen(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
        user_answer_factory,
    ):
        """Unseen упражнения приоритизируются (is_seen=0 сортируется первым)."""
        user = await user_factory()
        category = await category_factory()

        # Создаём ровно 5 seen и 5 unseen с непересекающимися ответами
        seen_ids = set()
        for i in range(5):
            ex = await exercise_factory(
                category_id=category.id,
                answer=f"seen_{i}",
                content=_make_exam22_content(),
            )
            await user_answer_factory(
                user_id=user.id, exercise_id=ex.id, category_id=category.id,
            )
            seen_ids.add(ex.id)

        unseen_ids = set()
        for i in range(5):
            ex = await exercise_factory(
                category_id=category.id,
                answer=f"unseen_{i}",
                content=_make_exam22_content(),
            )
            unseen_ids.add(ex.id)

        result = await exercise_repository.get_exam_22_exercises(category.id, user.id)

        assert len(result) == 5
        result_ids = {ex.id for ex in result}
        # Все unseen должны быть выбраны, т.к. их ровно 5 и они совместимы
        assert result_ids == unseen_ids

    async def test_incompatible_exercises_skipped(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
    ):
        """Упражнения с пересекающимися present/answer не попадают в один набор."""
        user = await user_factory()
        category = await category_factory()

        # ex1: answer="X", other_devices=["Y"] → present = {X, Y}
        # ex2: answer="Y", other_devices=[]   → answer {Y} пересекается с present ex1
        # Эти два несовместимы
        await exercise_factory(
            category_id=category.id, answer="X",
            content=_make_exam22_content(["Y"]),
        )
        await exercise_factory(
            category_id=category.id, answer="Y",
            content=_make_exam22_content([]),
        )
        # Добавим ещё 5 совместимых, чтобы CTE мог найти путь
        for i in range(5):
            await exercise_factory(
                category_id=category.id, answer=f"ok_{i}",
                content=_make_exam22_content(),
            )

        result = await exercise_repository.get_exam_22_exercises(category.id, user.id)

        assert len(result) == 5
        result_answers = {ex.answer for ex in result}
        # X и Y не могут быть в одном наборе
        assert not ({"X", "Y"} <= result_answers)

    async def test_semicolon_multi_answer(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
    ):
        """Упражнение с answer='A;B' — оба устройства считаются ответами."""
        user = await user_factory()
        category = await category_factory()

        await exercise_factory(
            category_id=category.id, answer="dev_a;dev_b",
            content=_make_exam22_content(),
        )
        # Остальные 6 совместимых с уникальными ответами
        for i in range(6):
            await exercise_factory(
                category_id=category.id, answer=f"solo_{i}",
                content=_make_exam22_content(),
            )

        result = await exercise_repository.get_exam_22_exercises(category.id, user.id)

        assert len(result) == 5

    async def test_filters_by_category(
        self,
        exercise_repository,
        user_factory,
        category_factory,
        exercise_factory,
    ):
        user = await user_factory()
        cat1 = await category_factory(name="Cat 1")
        cat2 = await category_factory(name="Cat 2")

        # 5 в cat1
        for i in range(5):
            await exercise_factory(
                category_id=cat1.id, answer=f"c1_{i}",
                content=_make_exam22_content(),
            )
        # 5 в cat2
        for i in range(5):
            await exercise_factory(
                category_id=cat2.id, answer=f"c2_{i}",
                content=_make_exam22_content(),
            )

        result = await exercise_repository.get_exam_22_exercises(cat1.id, user.id)

        assert len(result) == 5
        for ex in result:
            assert ex.category_id == cat1.id

    async def test_empty_category(
        self, exercise_repository, user_factory, category_factory,
    ):
        user = await user_factory()
        category = await category_factory()

        result = await exercise_repository.get_exam_22_exercises(category.id, user.id)

        assert list(result) == []

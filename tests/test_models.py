class TestModelRepr:
    async def test_user_repr(self, user_factory):
        user = await user_factory(telegram_id=123, username="ivan")
        r = repr(user)
        assert "123" in r
        assert "ivan" in r

    async def test_category_repr(self, category_factory):
        cat = await category_factory(name="Math")
        r = repr(cat)
        assert "Math" in r

    async def test_exercise_repr(self, category_factory, exercise_factory):
        cat = await category_factory()
        ex = await exercise_factory(category_id=cat.id)
        r = repr(ex)
        assert str(ex.id) in r

    async def test_user_answer_repr(self, user_factory, category_factory, exercise_factory, user_answer_factory):
        user = await user_factory()
        cat = await category_factory()
        ex = await exercise_factory(category_id=cat.id)
        ans = await user_answer_factory(user.id, ex.id, cat.id, is_correct=True)
        r = repr(ans)
        assert "True" in r

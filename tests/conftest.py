import os

# Stub env-vars required by app.config before any app imports
os.environ.setdefault("BOT_TOKEN", "fake-token-for-tests")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASS", "test")
os.environ.setdefault("REDIS_PASSWORD", "test")

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.database.base_model import BaseDBModel
from app.models import Category, Exercise, User, UserAnswer
from app.repositories import CategoryRepository, ExerciseRepository, UserAnswerRepository, UserRepository
from app.services.exercise_selector import ExerciseSelector


# ---------------------------------------------------------------------------
# Database engine & container
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def database_url():
    """Return async database URL from ``TEST_DATABASE_URL`` env-var (set in docker-compose)."""
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        raise RuntimeError("TEST_DATABASE_URL is not set. Run tests via: docker compose --profile test up")
    return url


@pytest.fixture(scope="session")
async def async_engine(database_url):
    engine = create_async_engine(database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(BaseDBModel.metadata.create_all)
    yield engine
    await engine.dispose()


# ---------------------------------------------------------------------------
# Per-test session with automatic rollback
# ---------------------------------------------------------------------------

@pytest.fixture
async def db_session(async_engine):
    """Async session wrapped in a transaction that is rolled back after each test.

    Every test gets an isolated DB state — all writes are discarded on teardown.
    """
    conn = await async_engine.connect()
    trans = await conn.begin()
    session = AsyncSession(bind=conn, expire_on_commit=False, join_transaction_mode="rollback_only")

    yield session

    await session.close()
    await trans.rollback()
    await conn.close()


# ---------------------------------------------------------------------------
# Repository fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def category_repository(db_session):
    return CategoryRepository(session=db_session)


@pytest.fixture
def user_repository(db_session):
    return UserRepository(session=db_session)


@pytest.fixture
def exercise_repository(db_session):
    return ExerciseRepository(session=db_session)


@pytest.fixture
def user_answer_repository(db_session):
    return UserAnswerRepository(session=db_session)


@pytest.fixture
def exercise_selector(exercise_repository, user_answer_repository):
    return ExerciseSelector(exercise_repository, user_answer_repository)


# ---------------------------------------------------------------------------
# Model factory fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def category_factory(db_session):
    async def _create(
        name: str = "Test Category",
        handler_type=None,
        parent_id: int | None = None,
    ) -> Category:
        category = Category(name=name, handler_type=handler_type, parent_id=parent_id)
        db_session.add(category)
        await db_session.flush()
        return category

    return _create


@pytest.fixture
def user_factory(db_session):
    _counter = 0

    async def _create(
        telegram_id: int | None = None,
        username: str = "testuser",
        full_name: str = "Test User",
    ) -> User:
        nonlocal _counter
        _counter += 1
        if telegram_id is None:
            telegram_id = 100_000 + _counter
        user = User(telegram_id=telegram_id, username=username, full_name=full_name)
        db_session.add(user)
        await db_session.flush()
        return user

    return _create


@pytest.fixture
def exercise_factory(db_session):
    async def _create(
        category_id: int,
        content: dict | None = None,
        answer: str = "42",
        explanation: str | None = None,
        is_active: bool = True,
        group_id: str | None = None,
        order_index: int | None = None,
    ) -> Exercise:
        import uuid as _uuid
        exercise = Exercise(
            category_id=category_id,
            content=content or {"text": "test question"},
            answer=answer,
            explanation=explanation,
            is_active=is_active,
            group_id=_uuid.UUID(group_id) if isinstance(group_id, str) else group_id,
            order_index=order_index,
        )
        db_session.add(exercise)
        await db_session.flush()
        return exercise

    return _create


@pytest.fixture
def user_answer_factory(db_session):
    async def _create(
        user_id: int,
        exercise_id: int,
        category_id: int,
        is_correct: bool = True,
        user_response: str = "42",
        solve_time: int = 10,
    ) -> UserAnswer:
        answer = UserAnswer(
            user_id=user_id,
            exercise_id=exercise_id,
            category_id=category_id,
            is_correct=is_correct,
            user_response=user_response,
            solve_time=solve_time,
        )
        db_session.add(answer)
        await db_session.flush()
        return answer

    return _create

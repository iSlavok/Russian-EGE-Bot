from collections.abc import AsyncGenerator

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.processors import ProcessorFactory
from app.repositories import CategoryRepository, ExerciseRepository, UserAnswerRepository, UserRepository
from app.services.category_service import CategoryService
from app.services.task_service import TaskService
from app.services.user_service import UserService


class AppProvider(Provider):
    scope = Scope.REQUEST

    @provide
    async def get_db_session(self) -> AsyncGenerator[AsyncSession]:
        async with get_session() as session:
            yield session

    exercise_repository = provide(ExerciseRepository)
    category_repository = provide(CategoryRepository)
    user_repository = provide(UserRepository)
    user_answer_repository = provide(UserAnswerRepository)

    processor_factory = provide(ProcessorFactory)

    user_service = provide(UserService)
    category_service = provide(CategoryService)
    task_service = provide(TaskService)

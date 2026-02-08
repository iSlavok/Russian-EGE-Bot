from datetime import UTC, datetime

from app.processors import ProcessorFactory
from app.repositories import ExerciseRepository, UserRepository
from app.schemas import CheckResult, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO


class TaskService:
    def __init__(
            self,
            processor_factory: ProcessorFactory,
            user_repository: UserRepository,
            exercise_repository: ExerciseRepository,
    ) -> None:
        self._processor_factory = processor_factory
        self._user_repository = user_repository
        self._exercise_repository = exercise_repository

    async def start_task(self, user: UserWithCategoryDTO) -> TaskUI:
        if not user.current_category:
            msg = "User does not have a current category set."
            raise ValueError(msg)
        if not user.current_category.handler_type:
            msg = "Current category does not have a handler type defined."
            raise ValueError(msg)
        processor = self._processor_factory.get_processor(user.current_category.handler_type)
        task_response = await processor.create_task(user)

        db_user = await self._user_repository.get_by_id_with_exercises(user.id)
        if not db_user:
            msg = "User not found."
            raise ValueError(msg)
        exercise_ids = [task_response.exercise_ids] \
            if isinstance(task_response.exercise_ids, int) \
            else task_response.exercise_ids
        exercises = []
        for exercise_id in exercise_ids:
            exercise = await self._exercise_repository.get_by_id(exercise_id)
            if not exercise:
                msg = f"Exercise with ID {exercise_id} not found."
                raise ValueError(msg)
            exercises.append(exercise)
        now = datetime.now(UTC)
        db_user.current_exercises = exercises
        db_user.exercise_started_at = now
        db_user.current_task_config = task_response.task_config.model_dump() if task_response.task_config else None
        await self._user_repository.flush([db_user])

        return task_response.task_ui

    async def check_answer(
            self,
            user: UserWithExercisesDTO,
            user_answer: str,
    ) -> CheckResult:
        if not user.current_category:
            msg = "User does not have a current category set."
            raise ValueError(msg)
        if not user.current_category.handler_type:
            msg = "Current category does not have a handler type defined."
            raise ValueError(msg)
        processor = self._processor_factory.get_processor(user.current_category.handler_type)
        return await processor.process_answer(user, user_answer)

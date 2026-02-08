from abc import ABC, abstractmethod
from datetime import UTC, datetime

from app.models import UserAnswer
from app.processors.interface import TaskProcessor
from app.repositories import ExerciseRepository, UserAnswerRepository
from app.schemas import CheckResult, TaskResponse, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO


class BaseTaskProcessor(ABC, TaskProcessor):
    def __init__(self, exercise_repository: ExerciseRepository, answer_repository: UserAnswerRepository) -> None:
        self._exercise_repository = exercise_repository
        self._answer_repository = answer_repository

    @abstractmethod
    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        pass

    @abstractmethod
    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        pass

    async def _process_answer_single_exercise(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises:
            msg = "User has no current exercises to check answer for"
            raise ValueError(msg)
        exercise = user.current_exercises[0]

        is_correct = user_answer == exercise.answer

        solve_start_at = user.exercise_started_at
        now = datetime.now(UTC)
        solve_time = int((now - solve_start_at).total_seconds()) if solve_start_at else 0
        answer = UserAnswer(
            is_correct=is_correct,
            user_response=user_answer,
            solve_time=solve_time,
            user_id=user.id,
            exercise_id=exercise.id,
            category_id=user.current_category_id,
        )
        self._answer_repository.add(answer)

        return CheckResult(
            is_correct=is_correct,
            explanation=exercise.explanation,
        )

import uuid
from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import UTC, datetime

from app.exceptions import (
    InvalidCategoryStructureError,
    NoCategoryError,
    NoCurrentExercisesError,
    TaskForUserNotFoundError,
)
from app.models import Exercise, UserAnswer
from app.processors.interface import TaskProcessor
from app.repositories import ExerciseRepository, UserAnswerRepository
from app.schemas import CategoryDTO, CheckResult, ExerciseDTO, TaskResponse, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.services.exercise_selector import ExerciseSelector


class BaseTaskProcessor(ABC, TaskProcessor):
    def __init__(
        self,
        exercise_repository: ExerciseRepository,
        answer_repository: UserAnswerRepository,
        exercise_selector: ExerciseSelector,
    ) -> None:
        self._exercise_repository = exercise_repository
        self._answer_repository = answer_repository
        self._exercise_selector = exercise_selector

    @abstractmethod
    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        pass

    @abstractmethod
    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        pass

    @staticmethod
    def _require_category(user: UserWithCategoryDTO) -> CategoryDTO:
        """Validates that user has a current category and returns it."""
        if user.current_category is None:
            raise NoCategoryError
        return user.current_category

    def _require_parent_category_id(self, user: UserWithCategoryDTO) -> int:
        """Validates that user has a current category with a parent and returns the parent_id."""
        category = self._require_category(user)
        if category.parent_id is None:
            raise InvalidCategoryStructureError
        return category.parent_id

    async def _fetch_exercise(self, category_id: int, user_id: int) -> Exercise:
        """Fetches one exercise using smart selection or raises TaskForUserNotFoundError."""
        exercises = await self._exercise_selector.select_smart(
            category_id=category_id,
            user_id=user_id,
            limit=1,
        )
        if not exercises:
            raise TaskForUserNotFoundError(user_id)
        return exercises[0]

    async def _fetch_exercises(self, category_id: int, user_id: int, count: int) -> Sequence[Exercise]:
        exercises = await self._exercise_selector.select_smart(
            category_id=category_id,
            user_id=user_id,
            limit=count,
        )
        if len(exercises) < count:
            raise TaskForUserNotFoundError(user_id)
        return exercises

    @staticmethod
    def _compute_solve_time(user: UserWithExercisesDTO) -> int:
        """Computes the time in seconds since the exercise was started."""
        started = user.exercise_started_at
        if not started:
            return 0
        return int((datetime.now(UTC) - started).total_seconds())

    def _record_answer(
        self,
        user: UserWithExercisesDTO,
        exercise_id: int,
        is_correct: bool,  # noqa: FBT001
        user_response: str,
        solve_time: int,
        group_id: uuid.UUID | None = None,
    ) -> None:
        """Creates and adds a UserAnswer record to the repository."""
        self._answer_repository.add(UserAnswer(
            is_correct=is_correct,
            user_response=user_response,
            solve_time=solve_time,
            user_id=user.id,
            exercise_id=exercise_id,
            category_id=user.current_category_id,
            group_id=group_id,
        ))

    @staticmethod
    def _get_ordered_exercises(user: UserWithExercisesDTO, exercise_ids: list[int]) -> list[ExerciseDTO]:
        """Returns exercises ordered by the given ID list (from task config)."""
        exercises_map = {ex.id: ex for ex in (user.current_exercises or [])}
        return [exercises_map[eid] for eid in exercise_ids]

    async def _process_answer_single_exercise(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises:
            raise NoCurrentExercisesError
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

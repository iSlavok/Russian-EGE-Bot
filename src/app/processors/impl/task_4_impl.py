import random

from app.exceptions import TaskForUserNotFoundError
from app.processors import BaseTaskProcessor
from app.processors.schemas import Task4Content
from app.schemas import CheckResult, TaskOption, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO


def _apply_stress(word: str, stress_index: int) -> str:
    # Пример: "банты" + stress_index=2 -> "бАнты"
    if stress_index < 1 or stress_index > len(word):
        msg = "Invalid stress index"
        raise ValueError(msg)
    i = stress_index - 1
    return f"{word[:i]}{word[i].upper()}{word[i + 1:]}"


class Task4DrillProcessor(BaseTaskProcessor):
    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        if user.current_category is None:
            msg = "User has no current category assigned"
            raise ValueError(msg)
        if user.current_category.parent_id is None:
            msg = "Current category must have a parent category for Task 4"
            raise ValueError(msg)

        exercises = await self._exercise_repository.get_random(
            category_id=user.current_category.parent_id,
            limit=1,
        )
        if not exercises:
            raise TaskForUserNotFoundError(user.id)
        exercise = exercises[0]

        content = Task4Content.model_validate(exercise.content)
        if not exercise.answer.isdigit():
            msg = "Exercise answer must be a digit representing stress index"
            raise ValueError(msg)
        answer = int(exercise.answer)

        correct_word = _apply_stress(content.word, answer)
        wrong_word = _apply_stress(content.word, content.incorrect_stress)
        options = [
            TaskOption(text=correct_word, value=str(answer)),
            TaskOption(text=wrong_word, value=str(content.incorrect_stress)),
        ]
        random.shuffle(options)

        return TaskResponse(
            task_ui=TaskUI(
                text=f"Выберите правильное ударение в слове: <b>{content.word}</b>",
                options=options,
            ),
            exercise_ids=exercise.id,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        return await self._process_answer_single_exercise(user, user_answer)

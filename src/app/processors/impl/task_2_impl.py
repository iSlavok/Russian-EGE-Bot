from app.processors import BaseTaskProcessor
from app.processors.schemas import Task2Content
from app.schemas import CheckResult, TaskOption, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO


class Task2DrillProcessor(BaseTaskProcessor):
    """Процессор для тренировочного режима задания 2.

    Пользователь должен определить, соответствует ли указанное лексическое значение
    слова его значению в данном контексте.
    """

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        parent_id = self._require_parent_category_id(user)
        exercise = await self._fetch_random_exercise(parent_id, user.id)

        content = Task2Content.model_validate(exercise.content)

        options = [
            TaskOption(text="Подходит", value="true"),
            TaskOption(text="Не подходит", value="false"),
        ]

        task_text = (
            "В предложении выделено слово. Определите, соответствует ли указанное лексическое значение его значению в "
            "данном контексте.\n\n"
            f"{content.text}\n\n"
            f"{content.word_with_definition}"
        )

        return TaskResponse(
            task_ui=TaskUI(
                text=task_text,
                options=options,
            ),
            exercise_ids=exercise.id,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        base_result = await self._process_answer_single_exercise(user, user_answer)

        if user.current_exercises:
            exercise = user.current_exercises[0]
            if exercise.answer == "false":
                return CheckResult(
                    is_correct=base_result.is_correct,
                    explanation=exercise.explanation,
                )

        return CheckResult(
            is_correct=base_result.is_correct,
            explanation=None,
        )

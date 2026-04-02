import random

from app.processors import BaseTaskProcessor
from app.processors.schemas import Task15DrillContent, Task15ExamConfig, Task15ExamContent
from app.schemas import CheckResult, TaskOption, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO
from app.utils import extract_sorted_digits

_N = "н"
_NN = "нн"

_ANSWER_DISPLAY = {_N: "Н", _NN: "НН"}

_MODE_FORMULATION = {
    "Н": "одна буква Н",
    "НН": "НН",
}


class Task15DrillProcessor(BaseTaskProcessor):
    """Тренировочный режим задания 15.

    Показывает предложение с пропуском в одном слове.
    Две кнопки с вариантами слова: с Н и с НН — фиксированный порядок.
    """

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        category = self._require_category(user)
        exercise = await self._fetch_random_exercise(category.id, user.id)

        content = Task15DrillContent.model_validate(exercise.content)

        sentence_gap = content.sentence.format(n="</i><b>(н/нн)</b><i>")
        word_n = content.word.format(n=_N.upper())
        word_nn = content.word.format(n=_NN.upper())

        task_text = (
            "Вставьте пропущенные буквы.\n\n"
            f"<i>{sentence_gap}</i>"
        )

        options = [
            TaskOption(text=word_n,  value=_N),
            TaskOption(text=word_nn, value=_NN),
        ]

        return TaskResponse(
            task_ui=TaskUI(text=task_text, options=options),
            exercise_ids=exercise.id,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises:
            msg = "User has no current exercises"
            raise ValueError(msg)
        exercise = user.current_exercises[0]

        is_correct = user_answer == exercise.answer

        solve_time = self._compute_solve_time(user)
        self._record_answer(user, exercise.id, is_correct, user_answer, solve_time)

        content = Task15DrillContent.model_validate(exercise.content)
        corrected_sentence = content.sentence.format(n=f"<u>{exercise.answer}</u>")
        correct_display = content.word.format(
            n=f"<u>{_ANSWER_DISPLAY.get(exercise.answer, exercise.answer).upper()}</u>",
        )

        if is_correct:
            explanation = (
                f"<b>Ответ:</b> {correct_display}\n\n"
                f"<i>{corrected_sentence}</i>\n\n"
                f"{exercise.explanation}"
            )
        else:
            user_display = content.word.format(n=f"<u>{_ANSWER_DISPLAY.get(user_answer, user_answer).upper()}</u>")
            explanation = (
                f"<b>Ваш ответ:</b> {user_display}\n"
                f"<b>Правильный ответ:</b> {correct_display}\n\n"
                f"<i>{corrected_sentence}</i>\n\n"
                f"{exercise.explanation}"
            )

        return CheckResult(is_correct=is_correct, explanation=explanation)


class Task15ExamProcessor(BaseTaskProcessor):
    """Экзаменационный режим задания 15.

    Показывает предложение с пронумерованными пропусками (1)(2)...
    Тип задания (Н или НН) выбирается рандомно из доступных modes.
    Пользователь вводит номера позиций, где пишется нужный тип.
    """

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        category = self._require_category(user)
        exercise = await self._fetch_random_exercise(category.id, user.id)

        content = Task15ExamContent.model_validate(exercise.content)

        mode = random.choice(content.modes)

        formulation = _MODE_FORMULATION[mode]
        task_text = (
            f"Укажите все цифру(-ы), на месте которой(-ых) пишется <b>{formulation}</b>.\n\n"
            f"<i>{content.sentence}</i>"
        )

        config = Task15ExamConfig(
            mode=mode,
        )

        return TaskResponse(
            task_ui=TaskUI(text=task_text, options=None),
            exercise_ids=exercise.id,
            task_config=config,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises:
            msg = "User has no current exercises"
            raise ValueError(msg)
        if user.current_task_config is None:
            msg = "Task config is required for exam"
            raise ValueError(msg)

        config = Task15ExamConfig.model_validate(user.current_task_config)
        exercise = user.current_exercises[0]
        mode_answer = config.mode.lower()
        answers = exercise.answer.split(";")
        correct_answer = "".join(
            str(i + 1) for i, a in enumerate(answers) if a == mode_answer
        )
        user_digits = extract_sorted_digits(user_answer)
        is_correct = user_digits == correct_answer

        solve_time = self._compute_solve_time(user)
        self._record_answer(user, exercise.id, is_correct, user_answer, solve_time)

        content = Task15ExamContent.model_validate(exercise.content)

        if is_correct:
            explanation = f"<b>Ответ:</b> {correct_answer}"
        else:
            explanation = (
                f"<b>Ваш ответ:</b> {user_digits}\n"
                f"<b>Правильный ответ:</b> {correct_answer}"
            )

        explanation += (
            f"\n\n<i>{content.corrected_sentence}</i>\n\n"
            f"<b>Объяснение:</b>\n<blockquote expandable>{exercise.explanation}</blockquote>"
        )

        return CheckResult(is_correct=is_correct, explanation=explanation)

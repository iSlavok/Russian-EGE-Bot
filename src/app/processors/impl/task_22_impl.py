import random
import uuid
from datetime import UTC, datetime

from app.exceptions import TaskForUserNotFoundError
from app.models import UserAnswer
from app.processors import BaseTaskProcessor
from app.processors.schemas.task_22_schemas import (
    ALL_DEVICES,
    DEVICE_NAMES,
    Task22DrillConfig,
    Task22DrillContent,
    Task22ExamConfig,
)
from app.schemas import CheckResult, TaskOption, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO

_LABELS = ["А", "Б", "В", "Г", "Д"]
_EXAM_SENTENCES = 5
_EXAM_DISTRACTORS = 4

_DRILL_FORMULATION = "Определите средство выразительности."

_EXAM_FORMULATION = (
    "Прочитайте фрагменты текстов и определите, какое средство выразительности "
    "использовано в каждом предложении. Запишите цифры в порядке, "
    "соответствующем буквам."
)


class Task22DrillProcessor(BaseTaskProcessor):
    """Тренировочный режим задания 22.

    Показывает одно предложение. Кнопки — 5 средств (1 правильное + 4 дистрактора).
    Ответ — enum-значение выбранного средства.
    """

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        if user.current_category is None:
            msg = "User has no current category assigned"
            raise ValueError(msg)
        if user.current_category.parent_id is None:
            msg = "Current category must have a parent category for Task 7"
            raise ValueError(msg)

        exercises = await self._exercise_repository.get_random(
            category_id=user.current_category.parent_id,
            limit=1,
        )
        if not exercises:
            raise TaskForUserNotFoundError(user.id)
        exercise = exercises[0]

        content = Task22DrillContent.model_validate(exercise.content)
        found_devices = exercise.answer.split(";")
        target = random.choice(found_devices)

        options_values = [target, *content.distractor_devices]
        random.shuffle(options_values)
        options = [
            TaskOption(text=DEVICE_NAMES[v], value=v)
            for v in options_values
        ]

        task_text = f"{_DRILL_FORMULATION}\n\n{content.sentence}"

        return TaskResponse(
            task_ui=TaskUI(text=task_text, options=options),
            exercise_ids=exercise.id,
            task_config=Task22DrillConfig(target=target),
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises:
            msg = "User has no current exercises"
            raise ValueError(msg)
        exercise = user.current_exercises[0]

        found_devices = set(exercise.answer.split(";"))
        is_correct = user_answer in found_devices

        solve_start_at = user.exercise_started_at
        now = datetime.now(UTC)
        solve_time = int((now - solve_start_at).total_seconds()) if solve_start_at else 0

        self._answer_repository.add(UserAnswer(
            is_correct=is_correct,
            user_response=user_answer,
            solve_time=solve_time,
            user_id=user.id,
            exercise_id=exercise.id,
            category_id=user.current_category_id,
        ))

        content = Task22DrillContent.model_validate(exercise.content)
        drill_config = Task22DrillConfig.model_validate(user.current_task_config)

        correct_parts = []
        for d in found_devices:
            name = DEVICE_NAMES[d]
            if d == drill_config.target:
                name = f"<u>{name}</u>"
            correct_parts.append(name)
        correct_names = " / ".join(correct_parts)

        if is_correct:
            explanation = f"<b>Ответ:</b> {correct_names}"
        else:
            explanation = (
                f"<b>Ваш ответ:</b> {DEVICE_NAMES.get(user_answer, user_answer)}\n"
                f"<b>Правильный ответ:</b> {correct_names}"
            )

        explanation += f"\n\n{content.sentence}"

        return CheckResult(is_correct=is_correct, explanation=explanation)


class Task22ExamProcessor(BaseTaskProcessor):
    """Экзаменационный режим задания 22.

    Показывает 5 предложений (А–Д) и 9 пронумерованных средств (1–9).
    Пользователь вводит 5 цифр в порядке А–Д.
    Ответ проверяется индивидуально для каждого предложения.
    """

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        if user.current_category is None:
            msg = "User has no current category assigned"
            raise ValueError(msg)
        if user.current_category.parent_id is None:
            msg = "Current category must have a parent category for Task 7"
            raise ValueError(msg)

        exercises = await self._exercise_repository.get_exam_22_exercises(
            category_id=user.current_category.parent_id,
        )
        if len(exercises) < _EXAM_SENTENCES:
            raise TaskForUserNotFoundError(user.id)

        exercises = list(exercises[:_EXAM_SENTENCES])

        used: set[str] = set()
        for ex in exercises:
            content = Task22DrillContent.model_validate(ex.content)
            used.update(ex.answer.split(";"))
            used.update(content.other_devices)

        plausible: set[str] = set()
        for ex in exercises:
            content = Task22DrillContent.model_validate(ex.content)
            plausible.update(content.distractor_devices)
        plausible -= used

        absent_pool = ALL_DEVICES - used
        distractor_source = plausible if len(plausible) >= _EXAM_DISTRACTORS else absent_pool
        distractors = random.sample(sorted(distractor_source), _EXAM_DISTRACTORS)

        correct_devices = [random.choice(ex.answer.split(";")) for ex in exercises]

        device_options = correct_devices + distractors
        random.shuffle(device_options)

        sentences_text = "\n\n".join(
            f"<b>{label}.</b> {Task22DrillContent.model_validate(ex.content).sentence}"
            for label, ex in zip(_LABELS, exercises, strict=False)
        )
        options_text = "\n".join(
            f"{i + 1}. {DEVICE_NAMES[d]}"
            for i, d in enumerate(device_options)
        )
        task_text = f"{_EXAM_FORMULATION}\n\n{sentences_text}\n\n{options_text}"

        task_config = Task22ExamConfig(
            exercise_ids=[ex.id for ex in exercises],
            device_options=device_options,
        )

        return TaskResponse(
            task_ui=TaskUI(text=task_text, options=None),
            exercise_ids=[ex.id for ex in exercises],
            task_config=task_config,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises:
            msg = "User has no current exercises"
            raise ValueError(msg)

        task_config = Task22ExamConfig.model_validate(user.current_task_config)

        id_to_ex = {ex.id: ex for ex in user.current_exercises}
        exercises = [id_to_ex[eid] for eid in task_config.exercise_ids]

        digits = [c for c in user_answer if c.isdigit()]

        solve_start_at = user.exercise_started_at
        now = datetime.now(UTC)
        solve_time = int((now - solve_start_at).total_seconds()) if solve_start_at else 0

        shared_group_id = uuid.uuid4()
        all_correct = True

        correct_digits: list[str] = []
        user_digits_display: list[str] = []
        detail_lines: list[str] = []

        for i, exercise in enumerate(exercises):
            found_devices = set(exercise.answer.split(";"))
            correct_device = next(
                (d for d in task_config.device_options if d in found_devices), None,
            )
            correct_digit = str(task_config.device_options.index(correct_device) + 1) if correct_device else "?"
            correct_digits.append(correct_digit)

            digit = digits[i] if i < len(digits) else ""
            user_digits_display.append(digit or "-")

            if digit and 1 <= int(digit) <= len(task_config.device_options):
                selected_device = task_config.device_options[int(digit) - 1]
                is_ex_correct = selected_device in found_devices
            else:
                selected_device = None
                is_ex_correct = False

            if not is_ex_correct:
                all_correct = False

            if selected_device:
                self._answer_repository.add(UserAnswer(
                    is_correct=is_ex_correct,
                    user_response=selected_device,
                    solve_time=solve_time,
                    user_id=user.id,
                    exercise_id=exercise.id,
                    category_id=user.current_category_id,
                    group_id=shared_group_id,
                ))

            content = Task22DrillContent.model_validate(exercise.content)
            correct_name = DEVICE_NAMES.get(correct_device, correct_device) if correct_device else "?"
            detail_lines.append(f"<b>{_LABELS[i]}.</b> {content.sentence}\n→ {correct_name}")

        correct_answer_str = "".join(correct_digits)
        user_answer_str = "".join(user_digits_display)

        if all_correct:
            header = f"<b>Ответ:</b> {user_answer_str}"
        else:
            header = (
                f"<b>Ваш ответ:</b> {user_answer_str}\n"
                f"<b>Правильный ответ:</b> {correct_answer_str}"
            )

        details = "\n\n".join(detail_lines)
        explanation = f"{header}\n\n<blockquote expandable>{details}</blockquote>"

        return CheckResult(is_correct=all_correct, explanation=explanation)

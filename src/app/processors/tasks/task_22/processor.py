import random
import uuid

from app.exceptions import NoCurrentExercisesError, TaskForUserNotFoundError
from app.processors import BaseTaskProcessor
from app.schemas import CheckResult, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO

from .formatter import Task22Formatter, Task22Letter
from .schemas import (
    ALL_DEVICES,
    Task22DrillConfig,
    Task22DrillContent,
    Task22ExamConfig,
)

_EXAM_SENTENCES = 5
_EXAM_DISTRACTORS = 4


class Task22DrillProcessor(BaseTaskProcessor):
    """Тренировочный режим задания 22.

    Показывает одно предложение. Кнопки — 5 средств (1 правильное + 4 дистрактора).
    Ответ — enum-значение выбранного средства.
    """

    _formatter = Task22Formatter()

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        parent_id = self._require_parent_category_id(user)
        exercise = await self._fetch_exercise(parent_id, user.id)

        content = Task22DrillContent.model_validate(exercise.content)
        found_devices = exercise.answer.split(";")
        target = random.choice(found_devices)

        options_values = [target, *content.distractor_devices]
        random.shuffle(options_values)

        return TaskResponse(
            task_ui=TaskUI(
                view=self._formatter.drill_condition(content.sentence),
                options=self._formatter.drill_options(options_values),
            ),
            exercise_ids=exercise.id,
            task_config=Task22DrillConfig(target=target),
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises:
            raise NoCurrentExercisesError
        exercise = user.current_exercises[0]

        found_devices = exercise.answer.split(";")
        is_correct = user_answer in set(found_devices)

        solve_time = self._compute_solve_time(user)
        self._record_answer(user, exercise.id, is_correct, user_answer, solve_time)

        content = Task22DrillContent.model_validate(exercise.content)
        return CheckResult(
            is_correct=is_correct,
            result_view=self._formatter.drill_result(
                devices=found_devices,
                user_device=user_answer,
                sentence=content.sentence,
                is_correct=is_correct,
            ),
        )


class Task22ExamProcessor(BaseTaskProcessor):
    """Экзаменационный режим задания 22.

    Показывает 5 предложений (А–Д) и 9 пронумерованных средств (1–9).
    Пользователь вводит 5 цифр в порядке А–Д.
    Ответ проверяется индивидуально для каждого предложения.
    """

    _formatter = Task22Formatter()

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        parent_id = self._require_parent_category_id(user)

        exercises = await self._exercise_repository.get_exam_22_exercises(
            category_id=parent_id,
            user_id=user.id,
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

        sentences = [Task22DrillContent.model_validate(ex.content).sentence for ex in exercises]
        exercise_ids = [ex.id for ex in exercises]
        return TaskResponse(
            task_ui=TaskUI(
                view=self._formatter.condition(sentences=sentences, device_options=device_options),
                options=None,
            ),
            exercise_ids=exercise_ids,
            task_config=Task22ExamConfig(exercise_ids=exercise_ids, device_options=device_options),
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises:
            raise NoCurrentExercisesError

        task_config = Task22ExamConfig.model_validate(user.current_task_config)
        exercises = self._get_ordered_exercises(user, task_config.exercise_ids)
        device_options = task_config.device_options

        digits = [c for c in user_answer if c.isdigit()]
        solve_time = self._compute_solve_time(user)
        shared_group_id = uuid.uuid4()
        all_correct = True

        correct_digits: list[str] = []
        user_digits_display: list[str] = []
        letters: list[Task22Letter] = []

        for i, exercise in enumerate(exercises):
            found_devices = set(exercise.answer.split(";"))
            correct_device = next((d for d in device_options if d in found_devices), None)
            correct_digit = str(device_options.index(correct_device) + 1) if correct_device else "?"
            correct_digits.append(correct_digit)

            digit = digits[i] if i < len(digits) else ""
            user_digits_display.append(digit or "-")

            if digit and 1 <= int(digit) <= len(device_options):
                selected_device = device_options[int(digit) - 1]
                is_ex_correct = selected_device in found_devices
            else:
                selected_device = None
                is_ex_correct = False

            if not is_ex_correct:
                all_correct = False
            if selected_device:
                self._record_answer(user, exercise.id, is_ex_correct, selected_device, solve_time, shared_group_id)

            content = Task22DrillContent.model_validate(exercise.content)
            letters.append(Task22Letter(
                number=correct_digit,
                device=correct_device or "",
                sentence=content.sentence,
                wrong=digit != correct_digit,
            ))

        return CheckResult(
            is_correct=all_correct,
            result_view=self._formatter.result(
                correct_answer="".join(correct_digits),
                user_answer="".join(user_digits_display),
                letters=letters,
                device_options=device_options,
                is_correct=all_correct,
            ),
        )

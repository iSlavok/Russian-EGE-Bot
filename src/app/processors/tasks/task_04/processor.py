import random
import uuid

from app.exceptions import (
    InvalidExerciseCountError,
    InvalidExerciseDataError,
    MissingTaskConfigError,
    NoCurrentExercisesError,
)
from app.processors import BaseTaskProcessor
from app.schemas import CheckResult, TaskOption, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO

from .formatter import Task4Formatter
from .schemas import Task4Content, Task4ExamConfig

EXAM_WORDS_COUNT = 5


def _apply_stress(word: str, stress_index: int) -> str:
    # Пример: "банты" + stress_index=2 -> "бАнты"
    if stress_index < 1 or stress_index > len(word):
        msg = "Invalid stress index"
        raise ValueError(msg)
    i = stress_index - 1
    return f"{word[:i]}{word[i].upper()}{word[i + 1:]}"


class Task4DrillProcessor(BaseTaskProcessor):
    _formatter = Task4Formatter()

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        parent_id = self._require_parent_category_id(user)
        exercise = await self._fetch_exercise(parent_id, user.id)

        content = Task4Content.model_validate(exercise.content)
        if not exercise.answer.isdigit():
            raise InvalidExerciseDataError(exercise.id, "answer must be a digit")
        answer = int(exercise.answer)

        correct_word = _apply_stress(content.word, answer)
        wrong_word = _apply_stress(content.word, content.incorrect_stress)
        options = [
            TaskOption(text=correct_word, value=str(answer)),
            TaskOption(text=wrong_word, value=str(content.incorrect_stress)),
        ]
        random.shuffle(options)

        return TaskResponse(
            task_ui=TaskUI(view=self._formatter.drill_condition(content), options=options),
            exercise_ids=exercise.id,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        is_correct = await self._process_answer_single_exercise(user, user_answer)

        if not user.current_exercises:
            raise NoCurrentExercisesError
        exercise = user.current_exercises[0]

        return CheckResult(
            is_correct=is_correct,
            result_view=self._formatter.drill_result(exercise.explanation or "", is_correct=is_correct),
        )


class Task4ExamProcessor(BaseTaskProcessor):
    """Процессор для экзаменационного режима задания 4.

    Создает задание из 5 слов (2-4 правильных, остальные неправильные).
    Пользователь должен выбрать все правильные слова, введя их номера (например, "124").
    """

    _formatter = Task4Formatter()

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        parent_id = self._require_parent_category_id(user)
        exercises = await self._fetch_exercises(parent_id, user.id, EXAM_WORDS_COUNT)

        num_correct = random.randint(2, 4)
        correct_indices = set(random.sample(range(EXAM_WORDS_COUNT), num_correct))

        contents = []
        stress_positions = []
        for i, exercise in enumerate(exercises):
            content = Task4Content.model_validate(exercise.content)
            if not exercise.answer.isdigit():
                raise InvalidExerciseDataError(exercise.id, "answer must be a digit")
            correct_stress_index = int(exercise.answer)
            shown_stress = correct_stress_index if i in correct_indices else content.incorrect_stress
            contents.append(content)
            stress_positions.append(shown_stress)

        exercise_ids = [ex.id for ex in exercises]
        return TaskResponse(
            task_ui=TaskUI(view=self._formatter.condition(contents, stress_positions), options=None),
            exercise_ids=exercise_ids,
            task_config=Task4ExamConfig(
                exercise_ids=exercise_ids,
                stress_positions=stress_positions,
            ),
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises or len(user.current_exercises) != EXAM_WORDS_COUNT:
            raise InvalidExerciseCountError(EXAM_WORDS_COUNT, len(user.current_exercises or []))

        if user.current_task_config is None:
            raise MissingTaskConfigError

        config = Task4ExamConfig.model_validate(user.current_task_config)
        ordered_exercises = self._get_ordered_exercises(user, config.exercise_ids)

        user_selected = {int(char) for char in user_answer if char.isdigit()}
        correct_indices = set()
        for i, exercise in enumerate(ordered_exercises, start=1):
            if not exercise.answer.isdigit():
                raise InvalidExerciseDataError(exercise.id, "answer must be a digit")
            correct_stress_index = int(exercise.answer)
            shown_stress = config.stress_positions[i - 1]
            if shown_stress == correct_stress_index:
                correct_indices.add(i)

        is_correct = user_selected == correct_indices

        solve_time = self._compute_solve_time(user)
        group_id = uuid.uuid4()

        explanations = []
        for i, exercise in enumerate(ordered_exercises, start=1):
            word_is_correct = i in correct_indices
            user_selected_word = i in user_selected
            word_answer_is_correct = word_is_correct == user_selected_word

            self._record_answer(user, exercise.id, word_answer_is_correct, user_answer, solve_time, group_id)
            explanations.append(exercise.explanation or "")

        correct_numbers = "".join(str(i) for i in sorted(correct_indices))
        return CheckResult(
            is_correct=is_correct,
            result_view=self._formatter.result(explanations, correct_numbers, user_answer, is_correct=is_correct),
        )

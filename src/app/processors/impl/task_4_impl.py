import random
import uuid
from datetime import UTC, datetime

from app.exceptions import TaskForUserNotFoundError
from app.models import UserAnswer
from app.processors import BaseTaskProcessor
from app.processors.schemas import Task4Content, Task4ExamConfig
from app.schemas import CheckResult, TaskOption, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO

EXAM_WORDS_COUNT = 5


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
                text=f"Выберите правильное ударение в слове: <b>{content.word}</b>.",
                options=options,
            ),
            exercise_ids=exercise.id,
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        return await self._process_answer_single_exercise(user, user_answer)


class Task4ExamProcessor(BaseTaskProcessor):
    """Процессор для экзаменационного режима задания 4.

    Создает задание из 5 слов (2-4 правильных, остальные неправильные).
    Пользователь должен выбрать все правильные слова, введя их номера (например, "124").
    """

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        if user.current_category is None:
            msg = "User has no current category assigned"
            raise ValueError(msg)
        if user.current_category.parent_id is None:
            msg = "Current category must have a parent category for Task 4"
            raise ValueError(msg)

        exercises = await self._exercise_repository.get_random(
            category_id=user.current_category.parent_id,
            limit=EXAM_WORDS_COUNT,
        )
        if len(exercises) < EXAM_WORDS_COUNT:
            raise TaskForUserNotFoundError(user.id)

        num_correct = random.randint(2, 4)
        correct_indices = set(random.sample(range(EXAM_WORDS_COUNT), num_correct))

        words_with_stress = []
        stress_positions = []

        for i, exercise in enumerate(exercises):
            content = Task4Content.model_validate(exercise.content)
            if not exercise.answer.isdigit():
                msg = f"Exercise answer must be a digit representing stress index (exercise {exercise.id})"
                raise ValueError(msg)
            correct_stress_index = int(exercise.answer)

            is_correct = i in correct_indices
            stress_index = correct_stress_index if is_correct else content.incorrect_stress

            word_with_stress = _apply_stress(content.word, stress_index)
            words_with_stress.append(word_with_stress)
            stress_positions.append(stress_index)

        task_text = ("Укажите варианты ответов, в которых верно выделана буква, обозначающая ударный гласный звук. "
                     "Запишите номера ответов.\n\n")
        for i, word in enumerate(words_with_stress, start=1):
            task_text += f"{i}) {word}\n"

        exercise_ids = [ex.id for ex in exercises]
        return TaskResponse(
            task_ui=TaskUI(
                text=task_text,
                options=None,
            ),
            exercise_ids=exercise_ids,
            task_config=Task4ExamConfig(
                exercise_ids=exercise_ids,
                stress_positions=stress_positions,
            ),
        )

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises or len(user.current_exercises) != EXAM_WORDS_COUNT:
            msg = "User must have exactly 5 current exercises for TASK_4_EXAM"
            raise ValueError(msg)

        if user.current_task_config is None:
            msg = "Task config is required for TASK_4_EXAM"
            raise ValueError(msg)

        config = Task4ExamConfig.model_validate(user.current_task_config)

        exercises_map = {ex.id: ex for ex in user.current_exercises}
        ordered_exercises = [exercises_map[ex_id] for ex_id in config.exercise_ids]

        user_selected = {int(char) for char in user_answer if char.isdigit()}
        correct_indices = set()
        for i, exercise in enumerate(ordered_exercises, start=1):
            if not exercise.answer.isdigit():
                msg = f"Exercise answer must be a digit (exercise {exercise.id})"
                raise ValueError(msg)
            correct_stress_index = int(exercise.answer)

            shown_stress = config.stress_positions[i - 1]

            if shown_stress == correct_stress_index:
                correct_indices.add(i)

        is_correct = user_selected == correct_indices

        solve_start_at = user.exercise_started_at
        now = datetime.now(UTC)
        solve_time = int((now - solve_start_at).total_seconds()) if solve_start_at else 0

        group_id = uuid.uuid4()

        explanation = ""
        for i, exercise in enumerate(ordered_exercises, start=1):
            word_is_correct = i in correct_indices
            user_selected_word = i in user_selected

            word_answer_is_correct = word_is_correct == user_selected_word

            answer = UserAnswer(
                is_correct=word_answer_is_correct,
                user_response=user_answer,
                solve_time=solve_time,
                group_id=group_id,
                user_id=user.id,
                exercise_id=exercise.id,
                category_id=user.current_category_id,
            )
            self._answer_repository.add(answer)
            explanation += f"{i}) {exercise.explanation}\n"

        correct_numbers = "".join(str(i) for i in sorted(correct_indices))
        if not is_correct:
            explanation = f"Ваш ответ: {user_answer}\n" + explanation
            explanation = f"Правильный ответ: {correct_numbers}\n\n" + explanation
        else:
            explanation = f"Ответ: {correct_numbers}\n\n" + explanation

        return CheckResult(
            is_correct=is_correct,
            explanation=explanation,
        )

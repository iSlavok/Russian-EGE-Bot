import random
import uuid
from datetime import UTC, datetime

from app.exceptions import TaskForUserNotFoundError
from app.models import Exercise, UserAnswer
from app.processors import BaseTaskProcessor
from app.processors.schemas import Task13Content, Task13ExamConfig
from app.schemas import CheckResult, TaskOption, TaskResponse, TaskUI, UserWithExercisesDTO
from app.schemas.user_schemas import UserWithCategoryDTO

EXAM_SENTENCES = 5
CORRECT_COUNT_WEIGHTS = [4, 4, 1]
NI_COUNT_WEIGHTS = [4, 4, 1]

_TOGETHER = "TOGETHER"
_SEPARATE = "SEPARATE"

_ANSWER_DISPLAY = {
    _TOGETHER: "слитно",
    _SEPARATE: "раздельно",
}

_MODE_NE = "НЕ"
_MODE_NE_NI = "НЕ/НИ"


class Task13DrillProcessor(BaseTaskProcessor):

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        if user.current_category is None:
            msg = "User has no current category assigned"
            raise ValueError(msg)
        if user.current_category.parent_id is None:
            msg = "Current category must have a parent category"
            raise ValueError(msg)

        exercises = await self._exercise_repository.get_random(
            category_id=user.current_category.parent_id,
            limit=1,
        )
        if not exercises:
            raise TaskForUserNotFoundError(user.id)
        exercise = exercises[0]

        content = Task13Content.model_validate(exercise.content)

        task_text = (
            f"Укажите, как пишется частица <b>{content.particle}</b> в данном предложении.\n\n"
            f"<i>{content.sentence}</i>"
        )

        options = [
            TaskOption(text="Слитно", value=_TOGETHER),
            TaskOption(text="Раздельно", value=_SEPARATE),
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

        correct_display = _ANSWER_DISPLAY[exercise.answer]
        if is_correct:
            explanation = f"<b>Ответ:</b> {correct_display}\n\n{exercise.explanation}"
        else:
            user_display = _ANSWER_DISPLAY.get(user_answer, user_answer)
            explanation = (
                f"<b>Ваш ответ:</b> {user_display}\n"
                f"<b>Правильный ответ:</b> {correct_display}\n\n"
                f"{exercise.explanation}"
            )

        return CheckResult(is_correct=is_correct, explanation=explanation)


class Task13ExamProcessor(BaseTaskProcessor):

    async def create_task(self, user: UserWithCategoryDTO) -> TaskResponse:
        if user.current_category is None:
            msg = "User has no current category assigned"
            raise ValueError(msg)
        if user.current_category.parent_id is None:
            msg = "Current category must have a parent category"
            raise ValueError(msg)

        category_id = user.current_category.parent_id
        mode = random.choices([_MODE_NE, _MODE_NE_NI], weights=[90, 10])[0]
        answer_type = random.choice([_TOGETHER, _SEPARATE])
        correct_count = random.choices([2, 3, 4], weights=CORRECT_COUNT_WEIGHTS)[0]
        wrong_count = EXAM_SENTENCES - correct_count
        opposite_answer = _SEPARATE if answer_type == _TOGETHER else _TOGETHER

        if mode == _MODE_NE:
            all_exs = await self._fetch_ne_exercises(
                category_id, answer_type, opposite_answer, correct_count, wrong_count,
            )
        else:
            all_exs = await self._fetch_ne_ni_exercises(
                category_id, answer_type, opposite_answer, correct_count,
            )

        if all_exs is None:
            raise TaskForUserNotFoundError(user.id)

        random.shuffle(all_exs)
        correct_indices = [i for i, ex in enumerate(all_exs) if ex.answer == answer_type]

        answer_display = _ANSWER_DISPLAY[answer_type]
        particle_label = f"<b>{mode}</b>"

        task_text = (
            f"Укажите варианты ответов, в которых {particle_label} пишется "
            f"<b>{answer_display}</b>. Запишите номера ответов.\n\n"
        )
        for i, ex in enumerate(all_exs, start=1):
            content = Task13Content.model_validate(ex.content)
            task_text += f"{i}) {content.sentence}\n"

        exercise_ids = [ex.id for ex in all_exs]
        config = Task13ExamConfig(
            exercise_ids=exercise_ids,
            correct_indices=correct_indices,
            answer_type=answer_type,
            mode=mode,
        )

        return TaskResponse(
            task_ui=TaskUI(text=task_text, options=None),
            exercise_ids=exercise_ids,
            task_config=config,
        )

    async def _fetch_ne_exercises(
        self,
        category_id: int,
        answer_type: str,
        opposite_answer: str,
        correct_count: int,
        wrong_count: int,
    ) -> list[Exercise] | None:
        correct_exs = list(await self._exercise_repository.get_random_by_answer_and_content_value(
            category_id=category_id,
            answer=answer_type,
            content_field="particle",
            content_value="НЕ",
            limit=correct_count,
        ))
        wrong_exs = list(await self._exercise_repository.get_random_by_answer_and_content_value(
            category_id=category_id,
            answer=opposite_answer,
            content_field="particle",
            content_value="НЕ",
            limit=wrong_count,
        ))
        if len(correct_exs) < correct_count or len(wrong_exs) < wrong_count:
            return None
        return correct_exs + wrong_exs

    async def _fetch_ne_ni_exercises(
        self,
        category_id: int,
        answer_type: str,
        opposite_answer: str,
        correct_count: int,
    ) -> list[Exercise] | None:
        ni_count = random.choices([1, 2, 3], weights=NI_COUNT_WEIGHTS)[0]

        ni_exs = list(await self._exercise_repository.get_random_by_content_value(
            category_id=category_id,
            content_field="particle",
            content_value="НИ",
            limit=ni_count,
        ))
        if not ni_exs:
            return None
        ni_count = len(ni_exs)

        ni_correct_count = sum(1 for ex in ni_exs if ex.answer == answer_type)

        ne_total = EXAM_SENTENCES - ni_count
        ne_correct_needed = max(1, correct_count - ni_correct_count)
        ne_correct_needed = min(ne_correct_needed, ne_total - 1)
        ne_wrong_needed = ne_total - ne_correct_needed

        ne_correct_exs = list(await self._exercise_repository.get_random_by_answer_and_content_value(
            category_id=category_id,
            answer=answer_type,
            content_field="particle",
            content_value="НЕ",
            limit=ne_correct_needed,
        ))
        ne_wrong_exs = list(await self._exercise_repository.get_random_by_answer_and_content_value(
            category_id=category_id,
            answer=opposite_answer,
            content_field="particle",
            content_value="НЕ",
            limit=ne_wrong_needed,
        ))

        if len(ne_correct_exs) < ne_correct_needed or len(ne_wrong_exs) < ne_wrong_needed:
            return None

        return ni_exs + ne_correct_exs + ne_wrong_exs

    async def process_answer(self, user: UserWithExercisesDTO, user_answer: str) -> CheckResult:
        if not user.current_exercises or len(user.current_exercises) != EXAM_SENTENCES:
            msg = f"User must have exactly {EXAM_SENTENCES} exercises for exam"
            raise ValueError(msg)

        if user.current_task_config is None:
            msg = "Task config is required for exam"
            raise ValueError(msg)

        config = Task13ExamConfig.model_validate(user.current_task_config)

        correct_answer = "".join(str(i + 1) for i in sorted(config.correct_indices))
        user_digits = "".join(sorted(c for c in user_answer if c.isdigit()))
        is_correct = user_digits == correct_answer

        solve_start_at = user.exercise_started_at
        now = datetime.now(UTC)
        solve_time = int((now - solve_start_at).total_seconds()) if solve_start_at else 0

        exercises_map = {ex.id: ex for ex in user.current_exercises}
        ordered_exercises = [exercises_map[eid] for eid in config.exercise_ids]

        group_id = uuid.uuid4()
        details = ""

        for i, ex in enumerate(ordered_exercises):
            sentence_num = i + 1
            is_correct_sentence = i in config.correct_indices
            user_selected = str(sentence_num) in user_digits
            sentence_right = user_selected == is_correct_sentence

            content = Task13Content.model_validate(ex.content)
            answer_display = _ANSWER_DISPLAY[ex.answer]

            details += f"<b>{sentence_num})</b> {content.sentence}\n"
            details += f"<i>Пишется {answer_display}. {ex.explanation}</i>\n\n"

            self._answer_repository.add(UserAnswer(
                is_correct=sentence_right,
                user_response=user_answer,
                solve_time=solve_time,
                group_id=group_id,
                user_id=user.id,
                exercise_id=ex.id,
                category_id=user.current_category_id,
            ))

        if is_correct:
            explanation = f"<b>Ответ: {correct_answer}</b>"
        else:
            explanation = (
                f"Ваш ответ: {user_digits}\n"
                f"<b>Правильный ответ: {correct_answer}</b>"
            )

        explanation += f"\n\n<b>Объяснения:</b>\n<blockquote expandable>{details}</blockquote>"

        return CheckResult(is_correct=is_correct, explanation=explanation)

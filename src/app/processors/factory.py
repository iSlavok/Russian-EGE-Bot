from app.enums import HandlerType
from app.processors.base_processor import TaskProcessor
from app.processors.impl import (
    SkipProcessor,
    SoonProcessor,
    Task1ExamProcessor,
    Task4DrillProcessor,
    Task4ExamProcessor,
)
from app.repositories import ExerciseRepository, UserAnswerRepository

PROCESSOR_MAPPING = {
    HandlerType.TASK_1_EXAM: Task1ExamProcessor,
    HandlerType.TASK_4_DRILL: Task4DrillProcessor,
    HandlerType.TASK_4_EXAM: Task4ExamProcessor,
    HandlerType.SKIP: SkipProcessor,
    HandlerType.SOON: SoonProcessor,
}


class ProcessorFactory:
    def __init__(self, exercise_repository: ExerciseRepository, answer_repository: UserAnswerRepository) -> None:
        self._exercise_repository = exercise_repository
        self._answer_repository = answer_repository

    def get_processor(self, handler_type: HandlerType) -> TaskProcessor:
        processor_cls = PROCESSOR_MAPPING.get(handler_type)
        if not processor_cls:
            msg = f"Unsupported handler type: {handler_type}"
            raise ValueError(msg)

        return processor_cls(
            exercise_repository=self._exercise_repository,
            answer_repository=self._answer_repository,
        )

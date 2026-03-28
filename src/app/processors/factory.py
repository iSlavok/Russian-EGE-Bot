from app.enums import HandlerType
from app.processors.base_processor import TaskProcessor
from app.processors.impl import (
    SkipProcessor,
    SoonProcessor,
    Task1DrillProcessor,
    Task2DrillProcessor,
    Task3ExamProcessor,
    Task4DrillProcessor,
    Task4ExamProcessor,
    Task5DrillProcessor,
    Task5ExamProcessor,
    Task6ExamProcessor,
    Task7DrillProcessor,
    Task7ExamProcessor,
    Task8DrillProcessor,
    Task8ExamProcessor,
    Task9DrillProcessor,
    Task9ExamProcessor,
    Task10DrillProcessor,
    Task10ExamProcessor,
    Task11DrillProcessor,
    Task11ExamProcessor,
    Task12DrillProcessor,
    Task12ExamProcessor,
    Task13DrillProcessor,
    Task13ExamProcessor,
    Task14DrillProcessor,
    Task14ExamProcessor,
    Task15DrillProcessor,
    Task15ExamProcessor,
    Task16DrillProcessor,
    Task16ExamProcessor,
    Task17ExamProcessor,
    Task18ExamProcessor,
    Task19ExamProcessor,
    Task20ExamProcessor,
    Task21DrillProcessor,
    Task21ExamProcessor,
)
from app.repositories import ExerciseRepository, UserAnswerRepository

PROCESSOR_MAPPING = {
    HandlerType.TASK_1_DRILL: Task1DrillProcessor,
    HandlerType.TASK_2_DRILL: Task2DrillProcessor,
    HandlerType.TASK_3_EXAM: Task3ExamProcessor,
    HandlerType.TASK_4_DRILL: Task4DrillProcessor,
    HandlerType.TASK_4_EXAM: Task4ExamProcessor,
    HandlerType.TASK_5_DRILL: Task5DrillProcessor,
    HandlerType.TASK_5_EXAM: Task5ExamProcessor,
    HandlerType.TASK_6_EXAM: Task6ExamProcessor,
    HandlerType.TASK_7_DRILL: Task7DrillProcessor,
    HandlerType.TASK_7_EXAM: Task7ExamProcessor,
    HandlerType.TASK_8_DRILL: Task8DrillProcessor,
    HandlerType.TASK_8_EXAM: Task8ExamProcessor,
    HandlerType.TASK_9_DRILL: Task9DrillProcessor,
    HandlerType.TASK_9_EXAM: Task9ExamProcessor,
    HandlerType.TASK_10_DRILL: Task10DrillProcessor,
    HandlerType.TASK_10_EXAM: Task10ExamProcessor,
    HandlerType.TASK_11_DRILL: Task11DrillProcessor,
    HandlerType.TASK_11_EXAM: Task11ExamProcessor,
    HandlerType.TASK_12_DRILL: Task12DrillProcessor,
    HandlerType.TASK_12_EXAM: Task12ExamProcessor,
    HandlerType.TASK_13_DRILL: Task13DrillProcessor,
    HandlerType.TASK_13_EXAM: Task13ExamProcessor,
    HandlerType.TASK_14_DRILL: Task14DrillProcessor,
    HandlerType.TASK_14_EXAM: Task14ExamProcessor,
    HandlerType.TASK_15_DRILL: Task15DrillProcessor,
    HandlerType.TASK_15_EXAM: Task15ExamProcessor,
    HandlerType.TASK_16_DRILL: Task16DrillProcessor,
    HandlerType.TASK_16_EXAM: Task16ExamProcessor,
    HandlerType.TASK_17_EXAM: Task17ExamProcessor,
    HandlerType.TASK_18_EXAM: Task18ExamProcessor,
    HandlerType.TASK_19_EXAM: Task19ExamProcessor,
    HandlerType.TASK_20_EXAM: Task20ExamProcessor,
    HandlerType.TASK_21_DRILL: Task21DrillProcessor,
    HandlerType.TASK_21_EXAM: Task21ExamProcessor,
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

from loguru import logger

from app.enums import HandlerType
from app.exceptions import ProcessorNotFoundError
from app.processors._base.interface import TaskProcessor
from app.processors.tasks.generic import SkipProcessor, SoonProcessor
from app.processors.tasks.task_01 import Task1DrillProcessor
from app.processors.tasks.task_02 import Task2DrillProcessor
from app.processors.tasks.task_03 import Task3ExamProcessor
from app.processors.tasks.task_04 import Task4DrillProcessor, Task4ExamProcessor
from app.processors.tasks.task_05 import Task5DrillProcessor, Task5ExamProcessor
from app.processors.tasks.task_06 import Task6ExamProcessor
from app.processors.tasks.task_07 import Task7DrillProcessor, Task7ExamProcessor
from app.processors.tasks.task_08 import Task8DrillProcessor, Task8ExamProcessor
from app.processors.tasks.task_09_12 import (
    Task9DrillProcessor,
    Task9ExamProcessor,
    Task10DrillProcessor,
    Task10ExamProcessor,
    Task11DrillProcessor,
    Task11ExamProcessor,
    Task12DrillProcessor,
    Task12ExamProcessor,
)
from app.processors.tasks.task_13 import Task13DrillProcessor, Task13ExamProcessor
from app.processors.tasks.task_14 import Task14DrillProcessor, Task14ExamProcessor
from app.processors.tasks.task_15 import Task15DrillProcessor, Task15ExamProcessor
from app.processors.tasks.task_16 import Task16DrillProcessor, Task16ExamProcessor
from app.processors.tasks.task_17_20 import (
    Task17ExamProcessor,
    Task18ExamProcessor,
    Task19ExamProcessor,
    Task20ExamProcessor,
)
from app.processors.tasks.task_21 import Task21DrillProcessor, Task21ExamProcessor
from app.processors.tasks.task_22 import Task22DrillProcessor, Task22ExamProcessor
from app.processors.tasks.task_23_24 import Task23ExamProcessor, Task24ExamProcessor
from app.processors.tasks.task_25 import Task25ExamProcessor
from app.processors.tasks.task_26 import Task26ExamProcessor
from app.repositories import ExerciseRepository, UserAnswerRepository
from app.services.exercise_selector import ExerciseSelector

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
    HandlerType.TASK_22_DRILL: Task22DrillProcessor,
    HandlerType.TASK_22_EXAM: Task22ExamProcessor,
    HandlerType.TASK_23_EXAM: Task23ExamProcessor,
    HandlerType.TASK_24_EXAM: Task24ExamProcessor,
    HandlerType.TASK_25_EXAM: Task25ExamProcessor,
    HandlerType.TASK_26_EXAM: Task26ExamProcessor,
    HandlerType.SKIP: SkipProcessor,
    HandlerType.SOON: SoonProcessor,
}


class ProcessorFactory:
    def __init__(
        self,
        exercise_repository: ExerciseRepository,
        answer_repository: UserAnswerRepository,
        exercise_selector: ExerciseSelector,
    ) -> None:
        self._exercise_repository = exercise_repository
        self._answer_repository = answer_repository
        self._exercise_selector = exercise_selector

    def get_processor(self, handler_type: HandlerType) -> TaskProcessor:
        processor_cls = PROCESSOR_MAPPING.get(handler_type)
        if not processor_cls:
            logger.warning("No processor found for handler_type={}", handler_type)
            raise ProcessorNotFoundError(str(handler_type))

        logger.debug("Using processor {} for handler_type={}", processor_cls.__name__, handler_type)
        return processor_cls(
            exercise_repository=self._exercise_repository,
            answer_repository=self._answer_repository,
            exercise_selector=self._exercise_selector,
        )

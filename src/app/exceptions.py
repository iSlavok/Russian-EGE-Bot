class AppError(Exception):
    """Base class for all exceptions in the app."""


class NotFoundError(AppError):
    """Raised when a requested resource is not found."""
    def __init__(self, message: str) -> None:
        super().__init__(message)


class TaskProcessorError(AppError):
    """Raised when there is an error in the task processing."""
    def __init__(self, message: str) -> None:
        super().__init__(message)


class CategoryNotFoundError(NotFoundError):
    """Raised when a requested category is not found."""
    def __init__(self, category_id: int) -> None:
        super().__init__(f"Category with ID {category_id} not found")


class TaskForUserNotFoundError(NotFoundError):
    """Raised when a task for a user is not found."""
    def __init__(self, user_id: int) -> None:
        super().__init__(f"Task for user with ID {user_id} not found")


class UserNotFoundError(NotFoundError):
    def __init__(self, user_id: int) -> None:
        super().__init__(f"User with ID {user_id} not found")


class ExerciseNotFoundError(NotFoundError):
    def __init__(self, exercise_id: int) -> None:
        super().__init__(f"Exercise with ID {exercise_id} not found")


class InvalidUserStateError(TaskProcessorError):
    """Пользователь в невалидном состоянии для запрошенной операции."""


class NoCategoryError(InvalidUserStateError):
    def __init__(self) -> None:
        super().__init__("User does not have a current category set")


class NoHandlerTypeError(InvalidUserStateError):
    def __init__(self) -> None:
        super().__init__("Current category does not have a handler type defined")


class NoCurrentExercisesError(InvalidUserStateError):
    def __init__(self) -> None:
        super().__init__("User has no current exercises")


class InvalidExerciseCountError(InvalidUserStateError):
    def __init__(self, expected: int, actual: int) -> None:
        super().__init__(f"Expected {expected} exercises, got {actual}")


class MissingTaskConfigError(InvalidUserStateError):
    def __init__(self) -> None:
        super().__init__("Task config is required but not set")


class InvalidCategoryStructureError(TaskProcessorError):
    def __init__(self, message: str = "Current category must have a parent category") -> None:
        super().__init__(message)


class InvalidExerciseDataError(TaskProcessorError):
    def __init__(self, exercise_id: int, detail: str) -> None:
        super().__init__(f"Invalid data in exercise {exercise_id}: {detail}")


class ProcessorNotFoundError(AppError):
    def __init__(self, handler_type: str) -> None:
        super().__init__(f"Unsupported handler type: {handler_type}")

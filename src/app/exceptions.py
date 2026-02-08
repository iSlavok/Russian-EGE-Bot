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

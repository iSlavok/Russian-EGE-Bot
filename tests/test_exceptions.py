import pytest

from app.exceptions import (
    AppError,
    CategoryNotFoundError,
    ExerciseNotFoundError,
    InvalidCategoryStructureError,
    InvalidExerciseCountError,
    InvalidExerciseDataError,
    InvalidUserStateError,
    MissingTaskConfigError,
    NoCategoryError,
    NoCurrentExercisesError,
    NoHandlerTypeError,
    NotFoundError,
    ProcessorNotFoundError,
    TaskForUserNotFoundError,
    TaskProcessorError,
    UserNotFoundError,
)


class TestExceptionHierarchy:
    def test_not_found_is_app_error(self):
        assert issubclass(NotFoundError, AppError)

    def test_task_processor_error_is_app_error(self):
        assert issubclass(TaskProcessorError, AppError)

    def test_category_not_found_is_not_found(self):
        assert issubclass(CategoryNotFoundError, NotFoundError)

    def test_user_not_found_is_not_found(self):
        assert issubclass(UserNotFoundError, NotFoundError)

    def test_exercise_not_found_is_not_found(self):
        assert issubclass(ExerciseNotFoundError, NotFoundError)

    def test_task_for_user_not_found_is_not_found(self):
        assert issubclass(TaskForUserNotFoundError, NotFoundError)

    def test_invalid_user_state_is_task_processor_error(self):
        assert issubclass(InvalidUserStateError, TaskProcessorError)

    def test_no_category_is_invalid_user_state(self):
        assert issubclass(NoCategoryError, InvalidUserStateError)

    def test_no_handler_type_is_invalid_user_state(self):
        assert issubclass(NoHandlerTypeError, InvalidUserStateError)

    def test_no_current_exercises_is_invalid_user_state(self):
        assert issubclass(NoCurrentExercisesError, InvalidUserStateError)

    def test_invalid_exercise_count_is_invalid_user_state(self):
        assert issubclass(InvalidExerciseCountError, InvalidUserStateError)

    def test_missing_task_config_is_invalid_user_state(self):
        assert issubclass(MissingTaskConfigError, InvalidUserStateError)

    def test_invalid_category_structure_is_task_processor(self):
        assert issubclass(InvalidCategoryStructureError, TaskProcessorError)

    def test_invalid_exercise_data_is_task_processor(self):
        assert issubclass(InvalidExerciseDataError, TaskProcessorError)

    def test_processor_not_found_is_app_error(self):
        assert issubclass(ProcessorNotFoundError, AppError)


class TestExceptionMessages:
    def test_category_not_found_message(self):
        exc = CategoryNotFoundError(42)
        assert "42" in str(exc)
        assert "Category" in str(exc)

    def test_user_not_found_message(self):
        exc = UserNotFoundError(7)
        assert "7" in str(exc)
        assert "User" in str(exc)

    def test_exercise_not_found_message(self):
        exc = ExerciseNotFoundError(99)
        assert "99" in str(exc)
        assert "Exercise" in str(exc)

    def test_task_for_user_not_found_message(self):
        exc = TaskForUserNotFoundError(5)
        assert "5" in str(exc)

    def test_no_category_message(self):
        exc = NoCategoryError()
        assert "category" in str(exc).lower()

    def test_no_handler_type_message(self):
        exc = NoHandlerTypeError()
        assert "handler" in str(exc).lower()

    def test_no_current_exercises_message(self):
        exc = NoCurrentExercisesError()
        assert "exercises" in str(exc).lower()

    def test_invalid_exercise_count_message(self):
        exc = InvalidExerciseCountError(expected=5, actual=3)
        assert "5" in str(exc)
        assert "3" in str(exc)

    def test_missing_task_config_message(self):
        exc = MissingTaskConfigError()
        assert "config" in str(exc).lower()

    def test_invalid_category_structure_default_message(self):
        exc = InvalidCategoryStructureError()
        assert "parent" in str(exc).lower()

    def test_invalid_category_structure_custom_message(self):
        exc = InvalidCategoryStructureError("custom msg")
        assert str(exc) == "custom msg"

    def test_invalid_exercise_data_message(self):
        exc = InvalidExerciseDataError(exercise_id=10, detail="bad content")
        assert "10" in str(exc)
        assert "bad content" in str(exc)

    def test_processor_not_found_message(self):
        exc = ProcessorNotFoundError("UNKNOWN_TYPE")
        assert "UNKNOWN_TYPE" in str(exc)


class TestExceptionsRaisable:
    def test_catch_as_app_error(self):
        with pytest.raises(AppError):
            raise CategoryNotFoundError(1)

    def test_catch_as_not_found(self):
        with pytest.raises(NotFoundError):
            raise UserNotFoundError(1)

    def test_catch_as_task_processor_error(self):
        with pytest.raises(TaskProcessorError):
            raise NoCategoryError()

    def test_catch_as_invalid_user_state(self):
        with pytest.raises(InvalidUserStateError):
            raise MissingTaskConfigError()

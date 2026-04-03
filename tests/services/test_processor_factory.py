import pytest

from app.enums import HandlerType
from app.exceptions import ProcessorNotFoundError
from app.processors import BaseTaskProcessor


class TestGetProcessor:
    def test_returns_processor_for_known_type(self, processor_factory):
        processor = processor_factory.get_processor(HandlerType.TASK_1_DRILL)
        assert isinstance(processor, BaseTaskProcessor)

    def test_all_handler_types_mapped(self, processor_factory):
        from app.processors.factory import PROCESSOR_MAPPING
        for handler_type in PROCESSOR_MAPPING:
            processor = processor_factory.get_processor(handler_type)
            assert isinstance(processor, BaseTaskProcessor)

    def test_unknown_type_raises(self, processor_factory):
        with pytest.raises(ProcessorNotFoundError):
            processor_factory.get_processor("NONEXISTENT_TYPE")

from enum import StrEnum

from app.enums.category_enums import HandlerType


class TestHandlerType:
    def test_is_str_enum(self):
        assert issubclass(HandlerType, StrEnum)

    def test_drill_types_exist(self):
        drills = [m for m in HandlerType if m.name.endswith("_DRILL")]
        assert len(drills) > 0

    def test_exam_types_exist(self):
        exams = [m for m in HandlerType if m.name.endswith("_EXAM")]
        assert len(exams) > 0

    def test_special_types(self):
        assert HandlerType.SOON == "SOON"
        assert HandlerType.SKIP == "SKIP"

    def test_string_value_matches_name(self):
        for member in HandlerType:
            assert member.value == member.name

    def test_task_1_drill(self):
        assert HandlerType.TASK_1_DRILL == "TASK_1_DRILL"
        assert str(HandlerType.TASK_1_DRILL) == "TASK_1_DRILL"

    def test_can_be_used_as_string(self):
        ht = HandlerType.TASK_4_EXAM
        assert f"type={ht}" == "type=TASK_4_EXAM"

    def test_total_count(self):
        assert len(HandlerType) == 42

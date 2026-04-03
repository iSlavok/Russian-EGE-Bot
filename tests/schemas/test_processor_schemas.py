import pytest
from pydantic import ValidationError

from app.processors.schemas import (
    Task1Content,
    Task2Content,
    Task3Content,
    Task4Content,
    Task4ExamConfig,
    Task5Content,
    Task5ExamConfig,
    Task5Paronym,
    Task6Content,
    Task6Type,
    Task7Content,
    Task7ExamConfig,
    Task8Content,
    Task8ExamConfig,
    Task13Content,
    Task13ExamConfig,
    Task14DrillContent,
    Task14ExamConfig,
    Task14ExamContent,
    Task15DrillContent,
    Task15ExamConfig,
    Task15ExamContent,
    Task16Content,
    Task16ExamConfig,
    Task21ColonRule,
    Task21CommaRule,
    Task21DashRule,
    Task21DrillContent,
    Task21ExamContent,
    Task21TaskType,
    Task25Content,
    Task26Content,
    Task2324Config,
    Task2324Content,
    TaskN9N12Content,
    TaskN9N12ExamConfig,
    TaskN17N20Content,
)


class TestTask1Content:
    def test_creation(self):
        c = Task1Content(text="Текст задания", instruction="Выберите ответ")
        assert c.text == "Текст задания"
        assert c.instruction == "Выберите ответ"

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            Task1Content(text="only text")


class TestTask2Content:
    def test_creation(self):
        c = Task2Content(text="Предложение", word_with_definition="Слово — значение")
        assert c.text == "Предложение"
        assert c.word_with_definition == "Слово — значение"

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            Task2Content(text="only")


class TestTask3Content:
    def test_creation(self):
        stmts = ["stmt1", "stmt2", "stmt3", "stmt4", "stmt5"]
        c = Task3Content(text="Фрагмент", statements=stmts)
        assert len(c.statements) == 5

    def test_empty_statements(self):
        c = Task3Content(text="Фрагмент", statements=[])
        assert c.statements == []


class TestTask4:
    def test_content(self):
        c = Task4Content(word="звонИт", incorrect_stress=1)
        assert c.word == "звонИт"
        assert c.incorrect_stress == 1
        assert c.context_before is None
        assert c.context_after is None

    def test_content_with_context(self):
        c = Task4Content(word="звонИт", incorrect_stress=1, context_before="он", context_after="мне")
        assert c.context_before == "он"

    def test_exam_config(self):
        cfg = Task4ExamConfig(exercise_ids=[1, 2, 3, 4, 5], stress_positions=[2, 1, 3, 2, 1])
        assert len(cfg.exercise_ids) == 5
        assert len(cfg.stress_positions) == 5


class TestTask5:
    def test_paronym(self):
        p = Task5Paronym(explanation="Объяснение", inflected_form="слова")
        assert p.explanation == "Объяснение"

    def test_content(self):
        paronyms = [Task5Paronym(explanation="e1", inflected_form="f1")]
        c = Task5Content(
            sentence="Предложение с {word}",
            words=["слово1"],
            paronyms=paronyms,
            secondary_number=0,
        )
        assert "{word}" in c.sentence

    def test_exam_config(self):
        cfg = Task5ExamConfig(exercise_ids=[1, 2, 3, 4, 5], wrong_sentence_index=2)
        assert cfg.wrong_sentence_index == 2


class TestTask6:
    def test_type_enum(self):
        assert Task6Type.REMOVE == "REMOVE"
        assert Task6Type.REPLACE == "REPLACE"

    def test_content(self):
        c = Task6Content(
            sentence="Предложение",
            task_type=Task6Type.REPLACE,
            sentence_with_markup="<u>слово</u>",
            corrected_sentence="<u>новое</u>",
        )
        assert c.task_type == Task6Type.REPLACE


class TestTask7:
    def test_content_minimal(self):
        c = Task7Content(phrase="фраза с {word}")
        assert c.incorrect_answer is None

    def test_content_with_incorrect(self):
        c = Task7Content(phrase="фраза с {word}", incorrect_answer="ошибка")
        assert c.incorrect_answer == "ошибка"

    def test_exam_config(self):
        cfg = Task7ExamConfig(exercise_ids=[1, 2, 3, 4, 5], wrong_phrase_index=3)
        assert cfg.wrong_phrase_index == 3


class TestTask8:
    def test_content_correct_sentence(self):
        c = Task8Content(sentence="Предложение")
        assert c.corrected_sentence is None

    def test_content_with_correction(self):
        c = Task8Content(sentence="Ошибка", corrected_sentence="<u>Исправлено</u>")
        assert c.corrected_sentence is not None

    def test_exam_config(self):
        cfg = Task8ExamConfig(
            exercise_ids=[1, 2, 3, 4, 5, 6, 7, 8, 9],
            error_type_order=["A", "B", "C", "D", "E"],
        )
        assert len(cfg.exercise_ids) == 9
        assert len(cfg.error_type_order) == 5


class TestTaskN9N12:
    def test_content(self):
        c = TaskN9N12Content(word="пр{letter}бежать", incorrect_letter="е")
        assert "{letter}" in c.word
        assert c.context_before is None

    def test_content_with_context(self):
        c = TaskN9N12Content(word="w", incorrect_letter="а", context_before="не", context_after="лся")
        assert c.context_before == "не"

    def test_exam_config(self):
        cfg = TaskN9N12ExamConfig(
            exercise_ids=[1, 2, 3, 4, 5, 6],
            correct_row_indices=[0, 2],
            words_per_row=2,
        )
        assert cfg.words_per_row == 2


class TestTask13:
    def test_content(self):
        c = Task13Content(sentence="(НЕ)большой дом", particle="НЕ")
        assert c.particle == "НЕ"

    def test_exam_config(self):
        cfg = Task13ExamConfig(
            exercise_ids=[1, 2, 3, 4, 5],
            correct_indices=[0, 3],
            answer_type="TOGETHER",
            mode="НЕ",
        )
        assert cfg.answer_type == "TOGETHER"


class TestTask14:
    def test_drill_content(self):
        c = Task14DrillContent(sentence="(ПО)ПРЕЖНЕМУ работал")
        assert "(ПО)" in c.sentence

    def test_exam_content(self):
        c = Task14ExamContent(
            sentence="(ПО)ПРЕЖНЕМУ (ТАК)ЖЕ",
            corrected_sentence="по-прежнему также",
            types=["HYPHEN", "TOGETHER"],
        )
        assert len(c.types) == 2

    def test_exam_config(self):
        cfg = Task14ExamConfig(
            exercise_ids=[1, 2, 3, 4, 5],
            correct_indices=[1, 4],
            answer_type="TOGETHER",
        )
        assert cfg.answer_type == "TOGETHER"


class TestTask15:
    def test_drill_content(self):
        c = Task15DrillContent(sentence="написа{n}ый текст", word="написа{n}ый")
        assert "{n}" in c.word

    def test_exam_content(self):
        c = Task15ExamContent(
            sentence="(1)текст (2)предложение",
            corrected_sentence="нн текст н предложение",
            modes=["Н", "НН"],
        )
        assert len(c.modes) == 2

    def test_exam_config(self):
        cfg = Task15ExamConfig(mode="НН")
        assert cfg.mode == "НН"


class TestTask16:
    def test_content(self):
        c = Task16Content(
            sentence="Он пришёл и сел",
            corrected_sentence="Он пришёл, и сел",
        )
        assert c.corrected_sentence != c.sentence

    def test_exam_config(self):
        cfg = Task16ExamConfig(exercise_ids=[1, 2, 3, 4, 5], correct_indices=[0, 2])
        assert cfg.correct_indices == [0, 2]


class TestTaskN17N20:
    def test_content(self):
        c = TaskN17N20Content(
            sentence="Предложение(1) текст(2) слово",
            correct_sentence="Предложение, текст, слово",
        )
        assert "(1)" in c.sentence


class TestTask21:
    def test_task_type_enum(self):
        assert Task21TaskType.COMMA == "COMMA"
        assert Task21TaskType.DASH == "DASH"
        assert Task21TaskType.COLON == "COLON"

    def test_comma_rules(self):
        assert Task21CommaRule.HOMOGENEOUS == "HOMOGENEOUS"
        assert Task21CommaRule.SSP == "SSP"

    def test_dash_rules(self):
        assert Task21DashRule.SUBJ_PRED == "SUBJ_PRED"

    def test_colon_rules(self):
        assert Task21ColonRule.BSP == "BSP"
        assert Task21ColonRule.DIRECT_SPEECH == "DIRECT_SPEECH"

    def test_drill_content(self):
        c = Task21DrillContent(text="Предложение с тире", task_type=Task21TaskType.DASH)
        assert c.task_type == Task21TaskType.DASH

    def test_exam_content(self):
        c = Task21ExamContent(
            full_text="(1)Предложение. (2)Ещё одно.",
            task_type=Task21TaskType.COMMA,
            answer_rule="HOMOGENEOUS",
        )
        assert c.answer_rule == "HOMOGENEOUS"


class TestTask2324:
    def test_content(self):
        c = Task2324Content(
            text="(1)Текст (2)предложений.",
            options=["Утв 1", "Утв 2", "Утв 3", "Утв 4", "Утв 5"],
        )
        assert len(c.options) == 5

    def test_config(self):
        cfg = Task2324Config(correct_digits="123", ask_incorrect=True)
        assert cfg.correct_digits == "123"
        assert cfg.ask_incorrect is True

    def test_config_ask_correct(self):
        cfg = Task2324Config(correct_digits="45", ask_incorrect=False)
        assert cfg.ask_incorrect is False


class TestTask25Content:
    def test_creation(self):
        c = Task25Content(task="Выпишите фразеологизм.", sentences="(31)Текст.")
        assert "фразеологизм" in c.task


class TestTask26Content:
    def test_creation(self):
        c = Task26Content(task="Средства связи.", sentences="(1)Предложение.")
        assert "связи" in c.task

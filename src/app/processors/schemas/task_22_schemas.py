from pydantic import BaseModel

DEVICE_NAMES: dict[str, str] = {
    "ALLITERATION":           "аллитерация",
    "ANAPHORA":               "анафора",
    "ANTITHESIS":             "антитеза",
    "ASSONANCE":              "ассонанс",
    "ASYNDETON":              "бессоюзие",
    "QUESTION_ANSWER_FORM":   "вопросно-ответная форма изложения",
    "HYPERBOLE":              "гипербола",
    "GRADATION":              "градация",
    "INVERSION":              "инверсия",
    "LEXICAL_REPEAT":         "лексический повтор",
    "LITOTES":                "литота",
    "METAPHOR":               "метафора",
    "METONYMY":               "метонимия",
    "POLYSYNDETON":           "многосоюзие",
    "PERSONIFICATION":        "олицетворение",
    "PARCELLATION":           "парцелляция",
    "RHETORICAL_QUESTION":    "риторический вопрос",
    "RHETORICAL_EXCLAMATION": "риторическое восклицание",
    "RHETORICAL_ADDRESS":     "риторическое обращение",
    "SYNTACTIC_PARALLELISM":  "синтаксический параллелизм",
    "SIMILE":                 "сравнение",
    "EPITHET":                "эпитет",
    "EPIPHORA":               "эпифора",
}

ALL_DEVICES: frozenset[str] = frozenset(DEVICE_NAMES.keys())


class Task22DrillContent(BaseModel):
    """Контент для drill-режима задания 22.

    sentence           - одно предложение с HTML-разметкой (<b>, <b><u>).
    distractor_devices - ровно 4 средства, которых нет в предложении.
    other_devices - другие средства, которые есть в предложении.
    excluded_devices - прочие средства, которых нет.
    """

    sentence: str
    distractor_devices: list[str]
    other_devices: list[str]
    excluded_devices: list[str]


class Task22DrillConfig(BaseModel):
    """Конфиг задачи для drill-режима задания 22.

    target - enum-значение средства, которое было показано как правильный вариант.
    """

    target: str


class Task22ExamConfig(BaseModel):
    """Конфиг задачи для exam-режима задания 22.

    exercise_ids   - 5 ID упражнений в порядке А–Д.
    device_options - 9 enum-значений средств в порядке отображения (1–9).
    """

    exercise_ids: list[int]
    device_options: list[str]

import re


def check_answer(
    user_answer: str,
    correct_answer: str,
    *,
    allow_dash_variations: bool = True,
    allow_space_omission: bool = True,
    allow_yo_normalization: bool = True,
) -> bool:
    """Проверяет ответ пользователя с гибкими правилами валидации.

    Args:
        user_answer: ответ пользователя
        correct_answer: правильный ответ
        allow_dash_variations: разрешить замену/пропуск тире на пробел
        allow_space_omission: разрешить пропуск пробелов
        allow_yo_normalization: разрешить замену ё на е

    Правила при allow_dash_variations=True:
    - Тире в правильном ответе: юзер может заменить на пробел или пропустить

    Правила при allow_space_omission=True:
    - Пробел в правильном ответе: юзер может только пропустить (НЕ может заменить на тире)

    Правила при allow_yo_normalization=True:
    - Буква ё: юзер может заменить на е

    Во всех случаях:
    - Регистр игнорируется
    - Юзер НЕ может добавить пробелы/тире там, где их нет
    """
    pattern = correct_answer.lower()
    pattern = re.escape(pattern)

    if allow_dash_variations:
        pattern = pattern.replace(r"\-", r"[-\s]?")

    if allow_space_omission:
        pattern = pattern.replace(r"\ ", r"\s?")

    if allow_yo_normalization:
        pattern = pattern.replace("ё", "[её]")

    regex = re.compile(f"^{pattern}$", re.IGNORECASE)
    return bool(regex.match(user_answer.strip()))

"""
Тест логики валидации ответов для task1exam
"""
import re


def _create_answer_pattern(correct_answer: str) -> re.Pattern:
    """Создает regex паттерн для проверки ответа."""
    pattern = correct_answer.lower()
    pattern = re.escape(pattern)
    # Тире → можно пропустить или заменить на пробел
    pattern = pattern.replace(r"\-", r"[-\s]?")
    # Пробел → можно только пропустить (НЕ заменять на тире)
    pattern = pattern.replace(r"\ ", r"\s?")
    pattern = pattern.replace("ё", "[её]")
    return re.compile(f"^{pattern}$", re.IGNORECASE)


def test_answer(correct: str, user_input: str) -> bool:
    """Проверяет ответ пользователя."""
    return bool(_create_answer_pattern(correct).match(user_input.strip()))


if __name__ == "__main__":
    print("=" * 80)
    print("ТЕСТ ВАЛИДАЦИИ ОТВЕТОВ ДЛЯ TASK1EXAM")
    print("=" * 80)

    # Тест 1: Ответ с тире
    print("\n1. Правильный ответ: 'какой-то'")
    test_cases = [
        ("какой-то", True, "с тире"),
        ("какойто", True, "без тире"),
        ("какой то", True, "пробел вместо тире"),
        ("КАКОЙ-ТО", True, "верхний регистр"),
        ("ка-който", False, "лишнее тире"),
        ("ка който", False, "лишний пробел"),
    ]
    for user_input, expected, description in test_cases:
        result = test_answer("какой-то", user_input)
        status = "[OK]" if result == expected else "[FAIL]"
        print(f"  {status} '{user_input}' ({description}): {result}")

    # Тест 2: Ответ с пробелом
    print("\n2. Правильный ответ: 'привет мир'")
    test_cases = [
        ("привет мир", True, "с пробелом"),
        ("приветмир", True, "без пробела"),
        ("привет-мир", False, "тире вместо пробела - ЗАПРЕЩЕНО"),
        ("ПРИВЕТ МИР", True, "верхний регистр"),
        ("при вет мир", False, "лишний пробел"),
        ("п ривет мир", False, "лишний пробел"),
    ]
    for user_input, expected, description in test_cases:
        result = test_answer("привет мир", user_input)
        status = "[OK]" if result == expected else "[FAIL]"
        print(f"  {status} '{user_input}' ({description}): {result}")

    # Тест 3: Ответ с ё
    print("\n3. Правильный ответ: 'ёжик'")
    test_cases = [
        ("ёжик", True, "с ё"),
        ("ежик", True, "е вместо ё"),
        ("ЁЖИК", True, "верхний регистр"),
        ("Ежик", True, "смешанный регистр"),
        ("ё жик", False, "лишний пробел"),
        ("е-жик", False, "лишнее тире"),
    ]
    for user_input, expected, description in test_cases:
        result = test_answer("ёжик", user_input)
        status = "[OK]" if result == expected else "[FAIL]"
        print(f"  {status} '{user_input}' ({description}): {result}")

    # Тест 4: Сложный ответ
    print("\n4. Правильный ответ: 'какой-то текст'")
    test_cases = [
        ("какой-то текст", True, "оригинал"),
        ("какойто текст", True, "без тире"),
        ("какой то текст", True, "пробел вместо тире"),
        ("какой-тотекст", True, "без пробела"),
        ("какойтотекст", True, "без тире и пробела"),
        ("какой  то текст", False, "двойной пробел"),
        ("ка-който текст", False, "лишнее тире"),
    ]
    for user_input, expected, description in test_cases:
        result = test_answer("какой-то текст", user_input)
        status = "[OK]" if result == expected else "[FAIL]"
        print(f"  {status} '{user_input}' ({description}): {result}")

    # Тест 5: Ответ без специальных символов
    print("\n5. Правильный ответ: 'привет'")
    test_cases = [
        ("привет", True, "оригинал"),
        ("ПРИВЕТ", True, "верхний регистр"),
        ("при вет", False, "добавлен пробел"),
        ("при-вет", False, "добавлено тире"),
    ]
    for user_input, expected, description in test_cases:
        result = test_answer("привет", user_input)
        status = "[OK]" if result == expected else "[FAIL]"
        print(f"  {status} '{user_input}' ({description}): {result}")

    print("\n" + "=" * 80)

import pytest

from app.utils.answer_validation import check_answer, extract_digits, extract_sorted_digits


class TestExtractSortedDigits:
    def test_already_sorted(self):
        assert extract_sorted_digits("123") == "123"

    def test_unsorted(self):
        assert extract_sorted_digits("321") == "123"

    def test_with_non_digit_chars(self):
        assert extract_sorted_digits("a3b1c2") == "123"

    def test_empty_string(self):
        assert extract_sorted_digits("") == ""

    def test_no_digits(self):
        assert extract_sorted_digits("abc") == ""

    def test_duplicate_digits(self):
        assert extract_sorted_digits("3211") == "1123"

    def test_single_digit(self):
        assert extract_sorted_digits("5") == "5"


class TestExtractDigits:
    def test_digits_only(self):
        assert extract_digits("456") == "456"

    def test_preserves_order(self):
        assert extract_digits("a4b5c6") == "456"

    def test_empty_string(self):
        assert extract_digits("") == ""

    def test_no_digits(self):
        assert extract_digits("hello") == ""

    def test_spaces_between(self):
        assert extract_digits("1 2 3") == "123"

    def test_single_digit(self):
        assert extract_digits("x7y") == "7"


class TestCheckAnswer:
    # --- Exact match ---
    def test_exact_match(self):
        assert check_answer("hello", "hello") is True

    def test_mismatch(self):
        assert check_answer("hello", "world") is False

    # --- Case insensitive ---
    def test_case_insensitive(self):
        assert check_answer("Hello", "hello") is True

    def test_case_insensitive_upper(self):
        assert check_answer("HELLO", "hello") is True

    # --- Strip whitespace ---
    def test_strip_leading_space(self):
        assert check_answer("  hello", "hello") is True

    def test_strip_trailing_space(self):
        assert check_answer("hello  ", "hello") is True

    # --- Dash variations (allow_dash_variations=True) ---
    def test_dash_replaced_by_space(self):
        assert check_answer("кое как", "кое-как") is True

    def test_dash_omitted(self):
        assert check_answer("коекак", "кое-как") is True

    def test_dash_kept(self):
        assert check_answer("кое-как", "кое-как") is True

    def test_dash_variations_disabled(self):
        assert check_answer("кое как", "кое-как", allow_dash_variations=False) is False

    def test_dash_variations_disabled_exact(self):
        assert check_answer("кое-как", "кое-как", allow_dash_variations=False) is True

    def test_dash_variations_disabled_omitted(self):
        assert check_answer("коекак", "кое-как", allow_dash_variations=False) is False

    # --- Space omission (allow_space_omission=True) ---
    def test_space_omitted(self):
        assert check_answer("потому", "по тому") is True

    def test_space_kept(self):
        assert check_answer("по тому", "по тому") is True

    def test_space_cannot_be_replaced_by_dash(self):
        assert check_answer("по-тому", "по тому") is False

    def test_space_omission_disabled(self):
        assert check_answer("потому", "по тому", allow_space_omission=False) is False

    def test_space_omission_disabled_exact(self):
        assert check_answer("по тому", "по тому", allow_space_omission=False) is True

    # --- Yo normalization (allow_yo_normalization=True) ---
    def test_yo_to_ye(self):
        assert check_answer("елка", "ёлка") is True

    def test_yo_kept(self):
        assert check_answer("ёлка", "ёлка") is True

    def test_yo_normalization_disabled(self):
        assert check_answer("елка", "ёлка", allow_yo_normalization=False) is False

    def test_yo_normalization_disabled_exact(self):
        assert check_answer("ёлка", "ёлка", allow_yo_normalization=False) is True

    def test_yo_multiple(self):
        assert check_answer("еще", "ещё") is True

    # --- Cannot add spaces/dashes where there are none ---
    def test_cannot_add_dash(self):
        assert check_answer("при-ехал", "приехал") is False

    def test_cannot_add_space(self):
        assert check_answer("при ехал", "приехал") is False

    # --- Combined flags ---
    def test_dash_and_yo(self):
        assert check_answer("кое где", "коё-где") is True

    def test_all_flags_off(self):
        result = check_answer(
            "елка",
            "ёлка",
            allow_dash_variations=False,
            allow_space_omission=False,
            allow_yo_normalization=False,
        )
        assert result is False

    def test_all_flags_off_exact(self):
        result = check_answer(
            "ёлка",
            "ёлка",
            allow_dash_variations=False,
            allow_space_omission=False,
            allow_yo_normalization=False,
        )
        assert result is True

    # --- Edge cases ---
    def test_empty_answer(self):
        assert check_answer("", "") is True

    def test_user_empty_correct_not(self):
        assert check_answer("", "hello") is False

    def test_numeric_answer(self):
        assert check_answer("42", "42") is True

    def test_numeric_mismatch(self):
        assert check_answer("43", "42") is False

    def test_special_regex_chars_in_answer(self):
        assert check_answer("(a+b)", "(a+b)") is True

    def test_answer_with_dot(self):
        assert check_answer("и.т.д.", "и.т.д.") is True

    def test_partial_match_rejected(self):
        assert check_answer("hello world", "hello") is False

    def test_partial_match_rejected_reverse(self):
        assert check_answer("hello", "hello world") is False

from sqlalchemy import ColumnElement

from app.models import Exercise


def answer_eq(answer: str) -> ColumnElement[bool]:
    return Exercise.answer == answer


def answer_ne(answer: str) -> ColumnElement[bool]:
    return Exercise.answer != answer


def content_exists(field: str) -> ColumnElement[bool]:
    return Exercise.content[field].as_string().isnot(None)


def content_eq(field: str, value: str) -> ColumnElement[bool]:
    return Exercise.content[field].as_string() == value

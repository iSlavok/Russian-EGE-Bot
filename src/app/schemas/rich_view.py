from typing import Literal

from pydantic import BaseModel, Field


class Paragraph(BaseModel):
    kind: Literal["paragraph"] = "paragraph"
    text: str


class Divider(BaseModel):
    kind: Literal["divider"] = "divider"


class Quote(BaseModel):
    kind: Literal["quote"] = "quote"
    lines: list[str]


class NumberedList(BaseModel):
    kind: Literal["numbered_list"] = "numbered_list"
    items: list[str]
    quoted: bool = False
    paren: bool = False  # маркер "N)" вместо "N."
    start: int = 1


class BulletList(BaseModel):
    kind: Literal["bullet_list"] = "bullet_list"
    items: list[str]


class Collapsible(BaseModel):
    kind: Literal["collapsible"] = "collapsible"
    summary: str
    blocks: list["Block"]
    open: bool = False
    open_if_wrong: bool = False


type Block = Paragraph | Divider | Quote | NumberedList | BulletList | Collapsible


class TaskView(BaseModel):
    heading: str
    instruction: str
    blocks: list[Block] = Field(default_factory=list)
    footer: str | None = None


class AnswerLine(BaseModel):
    label: str
    values: list[str]
    user: str | None = None
    strike: bool = False


class ResultView(BaseModel):
    correct: bool
    answer: AnswerLine | None = None
    wrong_answer: AnswerLine | None = None
    note: AnswerLine | None = None
    blocks: list[Block] = Field(default_factory=list)


Collapsible.model_rebuild()

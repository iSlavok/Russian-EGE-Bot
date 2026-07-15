from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.rich_view import Block, TaskView

HARD_BREAK = "  \n"  # жёсткий перенос: одиночный \n внутри <details> схлопывается


def _join_lines(lines: list[str], *, hard: bool) -> str:
    return (HARD_BREAK if hard else "\n").join(lines)


def _quote(lines: list[str], *, hard: bool) -> str:
    return _join_lines([f"> {ln}" for ln in lines], hard=hard)


def render_block(block: Block, *, correct: bool, in_details: bool) -> str:
    if block.kind == "paragraph":
        return block.text
    if block.kind == "divider":
        return "---"
    if block.kind == "quote":
        return _quote(block.lines, hard=in_details)
    if block.kind == "numbered_list":
        items = [f"{block.start + i}. {it}" for i, it in enumerate(block.items)]
        return _quote(items, hard=in_details) if block.quoted else _join_lines(items, hard=in_details)
    if block.kind == "bullet_list":
        return _join_lines([f"- {it}" for it in block.items], hard=in_details)
    msg = f"unknown block kind: {block.kind}"
    raise ValueError(msg)


def render_task(view: TaskView) -> str:
    body = "\n\n".join(render_block(b, correct=True, in_details=False) for b in view.blocks)
    out = f"### {view.heading}\n\n{view.instruction}\n\n---\n\n{body}"
    if view.footer:
        out += f"\n\n_{view.footer}_"
    return out

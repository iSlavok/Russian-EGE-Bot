import re

from app.schemas import AnswerLine, Block, ResultView, TaskView


class RichRenderer:
    """Рендер view-model → Rich Markdown. Все правила Rich-вёрстки — в одном месте."""

    HARD_BREAK = "  \n"  # внутри <details> одиночный \n схлопывается — нужен жёсткий перенос

    def render_task(self, view: TaskView) -> str:
        out = f"### {view.heading}\n\n{view.instruction}"
        if view.blocks:
            body = "\n\n".join(self.render_block(block, correct=True, in_details=False) for block in view.blocks)
            out += f"\n\n---\n\n{body}"
        if view.footer:
            out += f"\n\n_{view.footer}_"
        return out

    def render_result(self, view: ResultView) -> str:
        lines = ["**✅ Верно**" if view.correct else "**❌ Неверно**"]
        if view.wrong_answer:
            lines.append(self._answer_line(view.wrong_answer))
        if view.answer:
            lines.append(self._answer_line(view.answer))
        if view.note:
            lines.append(self._answer_line(view.note))
        body = "\n\n".join(self.render_block(block, correct=view.correct, in_details=False) for block in view.blocks)
        head = "\n\n".join(lines)
        return f"{head}\n\n{body}" if body else head

    def render_block(self, block: Block, *, correct: bool, in_details: bool) -> str:
        if block.kind == "paragraph":
            return block.text
        if block.kind == "divider":
            return "---"
        if block.kind == "quote":
            return self._quote(block.lines, hard=in_details)
        if block.kind == "numbered_list":
            sep = ")" if block.paren else "."
            items = [f"{block.start + i}{sep} {item}" for i, item in enumerate(block.items)]
            return self._quote(items, hard=in_details) if block.quoted else self._join(items, hard=in_details)
        if block.kind == "bullet_list":
            return self._join([f"- {item}" for item in block.items], hard=in_details)
        if block.kind == "collapsible":
            is_open = block.open or (block.open_if_wrong and not correct)
            tag = "<details open>" if is_open else "<details>"
            inner = "\n\n".join(self.render_block(child, correct=correct, in_details=True) for child in block.blocks)
            return f"{tag}<summary>{block.summary}</summary>\n\n{inner}\n\n</details>"
        msg = f"unknown block kind: {block.kind}"
        raise ValueError(msg)

    def _join(self, lines: list[str], *, hard: bool) -> str:
        return (self.HARD_BREAK if hard else "\n").join(lines)

    def _quote(self, lines: list[str], *, hard: bool) -> str:
        return self._join([f"> {line}" for line in lines], hard=hard)

    def _answer_line(self, answer: AnswerLine) -> str:
        if answer.strike:
            parts = [f"~~{value}~~" for value in answer.values]
        elif answer.user:
            highlighted = self._norm(answer.user)
            parts = [f"<u>{value}</u>" if self._norm(value) == highlighted else value for value in answer.values]
        else:
            parts = list(answer.values)
        return f"**{answer.label}:** " + " / ".join(parts)

    @staticmethod
    def _norm(value: str) -> str:
        return re.sub(r"\s+", "", value).lower()

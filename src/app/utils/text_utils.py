_TG_LIMIT = 4096
_CLOSEABLE_TAGS = frozenset(("blockquote", "b", "i", "u", "s", "code", "pre"))


def split_html_text(text: str, limit: int = _TG_LIMIT) -> list[str]:
    """Возвращает [text] если влезает, иначе [part1, part2].

    Разбивает по последнему пробелу до limit, не находящемуся внутри тега.
    Закрывает открытые теги в конце части 1 и переоткрывает их в начале части 2.
    """
    if len(text) <= limit:
        return [text]
    pos = _find_split_pos(text, limit)
    part1 = text[:pos].rstrip()
    part2 = text[pos:].lstrip()
    part1, reopeners = _close_open_tags(part1)
    return [part1, reopeners + part2]


def _find_split_pos(text: str, limit: int) -> int:
    """Последняя позиция пробела до limit, не внутри HTML-тега."""
    for i in range(limit - 1, 0, -1):
        if text[i] == " " and not _inside_tag(text, i):
            return i
    return limit


def _inside_tag(text: str, pos: int) -> bool:
    """True если позиция pos находится внутри <...>."""
    last_open = text.rfind("<", 0, pos)
    last_close = text.rfind(">", 0, pos)
    return last_open > last_close


def _close_open_tags(text: str) -> tuple[str, str]:
    """Находит незакрытые теги и возвращает (текст+закрывающие_теги, строка_для_переоткрытия).

    Сохраняет полный открывающий тег с атрибутами (например <blockquote expandable>).
    """
    stack: list[tuple[str, str]] = []  # (имя_тега, полный_открывающий_тег)
    i = 0
    while i < len(text):
        if text[i] == "<":
            end = text.find(">", i)
            if end == -1:
                break
            tag_content = text[i + 1 : end].strip()
            if tag_content.startswith("/"):
                name = tag_content[1:].split()[0].lower()
                if stack and stack[-1][0] == name:
                    stack.pop()
            else:
                name = tag_content.split()[0].lower()
                if name in _CLOSEABLE_TAGS:
                    full_tag = text[i : end + 1]  # e.g. "<blockquote expandable>"
                    stack.append((name, full_tag))
            i = end + 1
        else:
            i += 1

    closers = "".join(f"</{name}>" for name, _ in reversed(stack))
    reopeners = "".join(full_tag for _, full_tag in stack)
    return text + closers, reopeners

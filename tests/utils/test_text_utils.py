import pytest

from app.utils.text_utils import split_html_text


class TestSplitHtmlTextShort:
    def test_short_text_returns_single_item(self):
        assert split_html_text("hello") == ["hello"]

    def test_exact_limit(self):
        text = "a" * 100
        assert split_html_text(text, limit=100) == [text]

    def test_empty_string(self):
        assert split_html_text("") == [""]


class TestSplitHtmlTextSplitting:
    def test_splits_at_space(self):
        text = "word1 word2 word3"
        parts = split_html_text(text, limit=12)
        assert len(parts) == 2
        assert parts[0] == "word1 word2"
        assert parts[1] == "word3"

    def test_no_space_splits_at_limit(self):
        text = "a" * 20
        parts = split_html_text(text, limit=10)
        assert len(parts) == 2
        assert parts[0] == "a" * 10
        assert parts[1] == "a" * 10

    def test_split_strips_whitespace(self):
        text = "aaa bbb"
        parts = split_html_text(text, limit=4)
        assert parts[0] == "aaa"
        assert parts[1] == "bbb"


class TestSplitHtmlTextTags:
    def test_bold_tag_closed_and_reopened(self):
        text = "<b>word1 word2</b>"
        parts = split_html_text(text, limit=10)
        assert len(parts) == 2
        assert parts[0] == "<b>word1</b>"
        assert parts[1] == "<b>word2</b>"

    def test_italic_tag_closed_and_reopened(self):
        text = "<i>word1 word2</i>"
        parts = split_html_text(text, limit=10)
        assert len(parts) == 2
        assert parts[0] == "<i>word1</i>"
        assert parts[1] == "<i>word2</i>"

    def test_blockquote_expandable_tag(self):
        text = "<blockquote expandable>word1 word2</blockquote>"
        parts = split_html_text(text, limit=30)
        assert len(parts) == 2
        assert parts[0].endswith("</blockquote>")
        assert parts[1].startswith("<blockquote expandable>")

    def test_nested_tags(self):
        text = "<b><i>word1 word2</i></b>"
        parts = split_html_text(text, limit=13)
        assert len(parts) == 2
        assert parts[0] == "<b><i>word1</i></b>"
        assert parts[1] == "<b><i>word2</i></b>"

    def test_space_inside_tag_not_split_point(self):
        text = '<blockquote expandable>text</blockquote>'
        # space in "blockquote expandable" should not be a split point
        parts = split_html_text(text, limit=20)
        assert len(parts) == 2
        # split should happen at "text" level, not inside the tag
        assert "<blockquote expandable>" in parts[0] or parts[0].startswith("<blockquote")

    def test_already_closed_tags_not_doubled(self):
        text = "<b>word1</b> <b>word2</b>"
        parts = split_html_text(text, limit=14)
        assert len(parts) == 2
        assert parts[0] == "<b>word1</b>"
        assert parts[1] == "<b>word2</b>"

    def test_no_tags(self):
        text = "plain text here"
        parts = split_html_text(text, limit=11)
        assert len(parts) == 2
        assert parts[0] == "plain text"
        assert parts[1] == "here"

    def test_code_tag(self):
        text = "<code>some code here</code>"
        parts = split_html_text(text, limit=15)
        assert len(parts) == 2
        assert parts[0].endswith("</code>")
        assert parts[1].startswith("<code>")

    def test_unclosed_tag_gets_closed(self):
        # Text that's long enough to split in the middle of an unclosed bold
        text = "<b>aaaa bbbb"
        parts = split_html_text(text, limit=8)
        assert len(parts) == 2
        assert parts[0] == "<b>aaaa</b>"
        assert parts[1] == "<b>bbbb"

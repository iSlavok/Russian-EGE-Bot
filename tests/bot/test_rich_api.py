from bot.services.rich_api import build_rich_payload


def test_build_rich_payload_minimal():
    p = build_rich_payload(123, "**hi**", None)
    assert p == {"chat_id": 123, "rich_message": {"markdown": "**hi**"}}


def test_build_rich_payload_with_markup():
    p = build_rich_payload(123, "x", {"inline_keyboard": []})
    assert p["reply_markup"] == {"inline_keyboard": []}

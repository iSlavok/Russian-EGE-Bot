from __future__ import annotations

import json
from typing import TYPE_CHECKING

import aiohttp

if TYPE_CHECKING:
    from aiogram import Bot


def build_rich_payload(chat_id: int, markdown: str, reply_markup: dict | None) -> dict:
    payload: dict = {"chat_id": chat_id, "rich_message": {"markdown": markdown}}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    return payload


async def _call(bot: Bot, method: str, payload: dict) -> dict:
    url = bot.session.api.api_url(token=bot.token, method=method)
    async with aiohttp.ClientSession() as session, session.post(
        url, data=json.dumps(payload), headers={"Content-Type": "application/json"},
    ) as resp:
        if resp.status != 200:  # noqa: PLR2004
            text = (await resp.text())[:200]
            msg = f"{method} HTTP {resp.status}: {text}"
            raise RuntimeError(msg)
        return await resp.json()


async def send_rich_message(bot: Bot, chat_id: int, markdown: str, reply_markup: dict | None = None) -> int:
    res = await _call(bot, "sendRichMessage", build_rich_payload(chat_id, markdown, reply_markup))
    if not res.get("ok"):
        msg = f"sendRichMessage failed: {res}"
        raise RuntimeError(msg)
    return res["result"]["message_id"]

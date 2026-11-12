"""API tomonidan aholiga Telegram xabar yuborish (balon topshirildi, mashina yo'lda)."""

import asyncio
import logging
from collections.abc import Iterable

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter

logger = logging.getLogger(__name__)


class Notifier:
    def __init__(self, bot: Bot | None) -> None:
        self._bot = bot

    async def send(self, chat_id: int, text: str) -> None:
        if self._bot is None:
            logger.info("BOT_TOKEN yo'q, xabar yuborilmadi: chat_id=%s", chat_id)
            return
        try:
            await self._bot.send_message(chat_id, text)
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            try:
                await self._bot.send_message(chat_id, text)
            except TelegramAPIError:
                logger.exception("Xabar qayta yuborilmadi: chat_id=%s", chat_id)
        except TelegramAPIError:
            logger.exception("Xabar yuborilmadi: chat_id=%s", chat_id)

    async def broadcast(self, chat_ids: Iterable[int], text: str) -> None:
        for chat_id in chat_ids:
            await self.send(chat_id, text)
            await asyncio.sleep(0.05)  # Telegram limitlariga rioya (≈20 xabar/soniya)

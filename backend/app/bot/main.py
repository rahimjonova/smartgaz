"""Telegram-botni ishga tushirish: `python -m app.bot.main`."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.bot.handlers import common, menu, registration
from app.bot.middlewares import DbSessionMiddleware
from app.core.config import settings
from app.db.session import SessionLocal, engine

logger = logging.getLogger(__name__)


def build_dispatcher() -> Dispatcher:
    # MVP uchun xotirada saqlash. Productionda RedisStorage tavsiya etiladi.
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.update.outer_middleware(DbSessionMiddleware(SessionLocal))
    # Tartib muhim: buyruqlar -> FSM -> menyu (menyuda "catch-all" handler bor).
    dispatcher.include_routers(common.router, registration.router, menu.router)
    return dispatcher


async def main() -> None:
    logging.basicConfig(
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if not settings.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN .env faylida ko'rsatilmagan")

    bot = Bot(settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = build_dispatcher()
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Boshlash / asosiy menyu"),
            BotCommand(command="help", description="Yordam"),
            BotCommand(command="cancel", description="Joriy amalni bekor qilish"),
        ]
    )
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("SmartGaz bot ishga tushdi")
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

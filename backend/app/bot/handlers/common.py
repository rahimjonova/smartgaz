from html import escape

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.registration import start_registration
from app.bot.keyboards import main_menu_kb
from app.bot.texts import HELP_TEXT
from app.services import user_service

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    if message.from_user is None:
        return
    user = await user_service.get_user_by_telegram_id(session, message.from_user.id)
    if user is not None:
        await message.answer(
            f"Assalomu alaykum, <b>{escape(user.full_name)}</b>! 👋\nAsosiy menyu:",
            reply_markup=main_menu_kb(),
        )
        return
    await message.answer(
        "Assalomu alaykum! 👋\n<b>SmartGaz</b> botiga xush kelibsiz.\n"
        "Gaz balonga navbatga turish uchun avval ro'yxatdan o'ting."
    )
    await start_registration(message, state)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    if message.from_user is None:
        return
    user = await user_service.get_user_by_telegram_id(session, message.from_user.id)
    if user is not None:
        await message.answer("Amal bekor qilindi.", reply_markup=main_menu_kb())
    else:
        await message.answer(
            "Ro'yxatdan o'tish bekor qilindi. Qayta boshlash uchun /start",
            reply_markup=ReplyKeyboardRemove(),
        )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)

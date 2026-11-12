"""Asosiy menyu: navbat olish, navbat holati, mashina lokatsiyasi, profil, bekor qilish."""

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.formatters import format_driver_location, format_profile, format_queue_status
from app.bot.handlers.registration import start_registration
from app.bot.keyboards import (
    CancelOrderCallback,
    ProfileCallback,
    cancel_order_kb,
    main_menu_kb,
    profile_kb,
)
from app.bot.texts import BTN_CANCEL_ORDER, BTN_LOCATION, BTN_ORDER, BTN_PROFILE, BTN_STATUS
from app.core.exceptions import DomainError, OrderNotAllowedError
from app.models import User
from app.services import order_service, tracking_service, user_service

router = Router(name="menu")
router.message.filter(StateFilter(None))


async def _registered_user(message: Message, session: AsyncSession) -> User | None:
    if message.from_user is None:
        return None
    user = await user_service.get_user_by_telegram_id(session, message.from_user.id)
    if user is None:
        await message.answer("Avval ro'yxatdan o'ting: /start", reply_markup=ReplyKeyboardRemove())
    return user


@router.message(F.text == BTN_ORDER)
async def handle_create_order(message: Message, session: AsyncSession) -> None:
    user = await _registered_user(message, session)
    if user is None:
        return
    try:
        await order_service.create_order(session, user.id)
    except OrderNotAllowedError as exc:
        await message.answer(f"⚠️ {exc.message}", reply_markup=main_menu_kb())
        return
    except DomainError as exc:
        await message.answer(f"❗️ {exc.message}", reply_markup=main_menu_kb())
        return
    status = await order_service.get_queue_status(session, user.id)
    await message.answer(
        "✅ Siz navbatga muvaffaqiyatli qo'shildingiz!\n\n" + format_queue_status(status),
        reply_markup=main_menu_kb(),
    )


@router.message(F.text == BTN_STATUS)
async def handle_queue_status(message: Message, session: AsyncSession) -> None:
    user = await _registered_user(message, session)
    if user is None:
        return
    status = await order_service.get_queue_status(session, user.id)
    await message.answer(format_queue_status(status), reply_markup=main_menu_kb())


@router.message(F.text == BTN_LOCATION)
async def handle_driver_location(message: Message, session: AsyncSession) -> None:
    user = await _registered_user(message, session)
    if user is None:
        return
    location = await tracking_service.get_driver_location_for_user(session, user.id)
    if location is None:
        await message.answer(
            "🚚 Hozircha mahallangizga yo'lga chiqqan gaz mashinasi yo'q.\n"
            "Mashina yo'lga chiqqanda sizga xabar yuboramiz.",
            reply_markup=main_menu_kb(),
        )
        return
    if location.lat is None or location.lon is None:
        await message.answer(
            "🚚 Mashina yo'lga chiqqan, lekin GPS ma'lumot hali kelmadi. Birozdan so'ng urinib ko'ring.",
            reply_markup=main_menu_kb(),
        )
        return
    await message.answer_location(latitude=location.lat, longitude=location.lon)
    await message.answer(format_driver_location(location), reply_markup=main_menu_kb())


@router.message(F.text == BTN_PROFILE)
async def handle_profile(message: Message, session: AsyncSession) -> None:
    user = await _registered_user(message, session)
    if user is None:
        return
    await message.answer(format_profile(user), reply_markup=profile_kb())


@router.callback_query(StateFilter(None), ProfileCallback.filter(F.action == "edit"))
async def handle_profile_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await start_registration(callback.message, state)


@router.message(F.text == BTN_CANCEL_ORDER)
async def handle_cancel_order(message: Message, session: AsyncSession) -> None:
    user = await _registered_user(message, session)
    if user is None:
        return
    if await order_service.get_active_order(session, user.id) is None:
        await message.answer("Sizda faol navbat yo'q.", reply_markup=main_menu_kb())
        return
    await message.answer("Navbatni bekor qilmoqchimisiz?", reply_markup=cancel_order_kb())


@router.callback_query(StateFilter(None), CancelOrderCallback.filter())
async def handle_cancel_order_confirm(
    callback: CallbackQuery, callback_data: CancelOrderCallback, session: AsyncSession
) -> None:
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    await callback.message.edit_reply_markup(reply_markup=None)
    if callback_data.action != "yes":
        await callback.answer("Navbat saqlab qolindi")
        return
    user = await user_service.get_user_by_telegram_id(session, callback.from_user.id)
    if user is None:
        await callback.answer("Avval ro'yxatdan o'ting: /start", show_alert=True)
        return
    try:
        order = await order_service.cancel_order(session, user.id)
    except DomainError as exc:
        await callback.answer(exc.message, show_alert=True)
        return
    await callback.answer()
    await callback.message.answer(f"Navbat #{order.id} bekor qilindi.", reply_markup=main_menu_kb())


@router.message()
async def handle_unknown(message: Message) -> None:
    await message.answer("Menyudan kerakli bo'limni tanlang 👇", reply_markup=main_menu_kb())

"""Ro'yxatdan o'tish FSM: ism → telefon (contact) → viloyat → tuman → mahalla →
ko'cha → uy → gaz ID-karta (ixtiyoriy) → tasdiqlash."""

import re

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.formatters import format_registration_summary
from app.bot.keyboards import (
    RegionCallback,
    RegistrationConfirmCallback,
    contact_kb,
    main_menu_kb,
    regions_kb,
    registration_confirm_kb,
    skip_kb,
)
from app.bot.states import Registration
from app.bot.texts import BTN_SKIP
from app.core.exceptions import DomainError
from app.core.regions import REGIONS
from app.core.utils import clean_text, normalize_phone
from app.schemas.user import UserRegister
from app.services import user_service

router = Router(name="registration")

_LPG_CARD_RE = re.compile(r"^[A-Z0-9-]{4,32}$")


async def start_registration(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(Registration.full_name)
    await message.answer(
        "📝 <b>Ro'yxatdan o'tish</b> (bekor qilish: /cancel)\n\n"
        "Ism-familiyangizni kiriting.\nMasalan: <i>Aliyev Vali</i>",
        reply_markup=ReplyKeyboardRemove(),
    )


async def _read_text(message: Message, *, min_len: int, max_len: int, label: str) -> str | None:
    value = clean_text(message.text or "")
    if not (min_len <= len(value) <= max_len):
        await message.answer(f"⚠️ {label} {min_len}–{max_len} belgidan iborat bo'lishi kerak.")
        return None
    return value


# --------------------------------------------------------------------- 1. Ism-familiya
@router.message(Registration.full_name, F.text)
async def process_full_name(message: Message, state: FSMContext) -> None:
    value = await _read_text(message, min_len=3, max_len=150, label="Ism-familiya")
    if value is None:
        return
    if len(value.split()) < 2:
        await message.answer("⚠️ Iltimos, ism va familiyani to'liq kiriting.")
        return
    await state.update_data(full_name=value)
    await state.set_state(Registration.phone)
    await message.answer(
        "📱 Telefon raqamingizni pastdagi tugma orqali yuboring:", reply_markup=contact_kb()
    )


# --------------------------------------------------------------------- 2. Telefon (contact)
@router.message(Registration.phone, F.contact)
async def process_contact(message: Message, state: FSMContext) -> None:
    contact = message.contact
    if contact is None or message.from_user is None:
        return
    if contact.user_id != message.from_user.id:
        await message.answer(
            "⚠️ Iltimos, boshqa odamning emas, <b>o'zingizning</b> raqamingizni yuboring.",
            reply_markup=contact_kb(),
        )
        return
    try:
        phone = normalize_phone(contact.phone_number)
    except ValueError:
        await message.answer(
            "⚠️ Xizmat faqat O'zbekiston raqamlari (+998) uchun.", reply_markup=contact_kb()
        )
        return
    await state.update_data(phone_number=phone)
    await state.set_state(Registration.region)
    await message.answer("✅ Raqam qabul qilindi.", reply_markup=ReplyKeyboardRemove())
    await message.answer("📍 Viloyatingizni tanlang:", reply_markup=regions_kb())


@router.message(Registration.phone)
async def process_contact_invalid(message: Message) -> None:
    await message.answer(
        "Raqamni qo'lda yozmang — «📱 Telefon raqamni yuborish» tugmasini bosing.",
        reply_markup=contact_kb(),
    )


# --------------------------------------------------------------------- 3. Viloyat
@router.callback_query(Registration.region, RegionCallback.filter())
async def process_region(
    callback: CallbackQuery, callback_data: RegionCallback, state: FSMContext
) -> None:
    if not 0 <= callback_data.index < len(REGIONS):
        await callback.answer("Noto'g'ri tanlov", show_alert=True)
        return
    region = REGIONS[callback_data.index]
    await state.update_data(region=region)
    await state.set_state(Registration.district)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(f"📍 Viloyat: <b>{region}</b>")
        await callback.message.answer("Tuman (shahar) nomini kiriting:")
    await callback.answer()


@router.message(Registration.region)
async def process_region_invalid(message: Message) -> None:
    await message.answer("Viloyatni yuqoridagi tugmalardan tanlang:", reply_markup=regions_kb())


# --------------------------------------------------------------------- 4–7. Manzil
@router.message(Registration.district, F.text)
async def process_district(message: Message, state: FSMContext) -> None:
    value = await _read_text(message, min_len=2, max_len=100, label="Tuman nomi")
    if value is None:
        return
    await state.update_data(district=value)
    await state.set_state(Registration.mahalla)
    await message.answer("🏘 Mahalla (MFY) nomini kiriting:")


@router.message(Registration.mahalla, F.text)
async def process_mahalla(message: Message, state: FSMContext) -> None:
    value = await _read_text(message, min_len=2, max_len=150, label="Mahalla nomi")
    if value is None:
        return
    await state.update_data(mahalla=value)
    await state.set_state(Registration.street)
    await message.answer("🛣 Ko'cha nomini kiriting:")


@router.message(Registration.street, F.text)
async def process_street(message: Message, state: FSMContext) -> None:
    value = await _read_text(message, min_len=2, max_len=150, label="Ko'cha nomi")
    if value is None:
        return
    await state.update_data(street=value)
    await state.set_state(Registration.house_number)
    await message.answer("🏠 Xonadon (uy) raqamini kiriting:")


@router.message(Registration.house_number, F.text)
async def process_house_number(message: Message, state: FSMContext) -> None:
    value = await _read_text(message, min_len=1, max_len=20, label="Uy raqami")
    if value is None:
        return
    await state.update_data(house_number=value)
    await state.set_state(Registration.lpg_card)
    await message.answer(
        "💳 Maishiy gaz ID-karta raqamini kiriting (ixtiyoriy):", reply_markup=skip_kb()
    )


# --------------------------------------------------------------------- 8. Gaz ID-karta
@router.message(Registration.lpg_card, F.text)
async def process_lpg_card(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    card: str | None = None
    if raw != BTN_SKIP:
        card = raw.upper().replace(" ", "")
        if not _LPG_CARD_RE.fullmatch(card):
            await message.answer(
                "⚠️ Karta raqami 4–32 ta lotin harfi, raqam yoki «-» belgisidan iborat bo'lsin.",
                reply_markup=skip_kb(),
            )
            return
    await state.update_data(lpg_card_id=card)
    await state.set_state(Registration.confirm)
    await message.answer("Deyarli tayyor!", reply_markup=ReplyKeyboardRemove())
    await message.answer(
        format_registration_summary(await state.get_data()),
        reply_markup=registration_confirm_kb(),
    )


# --------------------------------------------------------------------- 9. Tasdiqlash
@router.callback_query(Registration.confirm, RegistrationConfirmCallback.filter(F.action == "ok"))
async def process_confirm(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    data = await state.get_data()
    try:
        payload = UserRegister(
            telegram_id=callback.from_user.id,
            full_name=data.get("full_name", ""),
            phone_number=data.get("phone_number", ""),
            region=data.get("region", ""),
            district=data.get("district", ""),
            mahalla=data.get("mahalla", ""),
            street=data.get("street", ""),
            house_number=data.get("house_number", ""),
            lpg_card_id=data.get("lpg_card_id"),
        )
    except ValidationError:
        await callback.answer("Ma'lumotlarda xatolik. Qaytadan kiriting.", show_alert=True)
        if isinstance(callback.message, Message):
            await start_registration(callback.message, state)
        return

    try:
        await user_service.register_user(session, payload)
    except DomainError as exc:
        await callback.answer(exc.message, show_alert=True)
        return

    await state.clear()
    await callback.answer("Saqlandi")
    if isinstance(callback.message, Message):
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            "✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!\nAsosiy menyu:", reply_markup=main_menu_kb()
        )


@router.callback_query(
    Registration.confirm, RegistrationConfirmCallback.filter(F.action == "restart")
)
async def process_restart(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.edit_reply_markup(reply_markup=None)
        await start_registration(callback.message, state)


# --------------------------------------------------------------------- noto'g'ri kiritish
@router.message(
    StateFilter(
        Registration.full_name,
        Registration.district,
        Registration.mahalla,
        Registration.street,
        Registration.house_number,
        Registration.lpg_card,
        Registration.confirm,
    )
)
async def process_unexpected(message: Message) -> None:
    await message.answer(
        "Iltimos, so'ralgan ma'lumotni matn ko'rinishida yuboring (/cancel — bekor qilish)."
    )

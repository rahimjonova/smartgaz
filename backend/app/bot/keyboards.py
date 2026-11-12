from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.bot.texts import (
    BTN_CANCEL_ORDER,
    BTN_LOCATION,
    BTN_ORDER,
    BTN_PROFILE,
    BTN_SEND_CONTACT,
    BTN_SKIP,
    BTN_STATUS,
)
from app.core.regions import REGIONS


class RegionCallback(CallbackData, prefix="region"):
    index: int


class RegistrationConfirmCallback(CallbackData, prefix="regconf"):
    action: str  # "ok" | "restart"


class CancelOrderCallback(CallbackData, prefix="ordcancel"):
    action: str  # "yes" | "no"


class ProfileCallback(CallbackData, prefix="profile"):
    action: str  # "edit"


def main_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text=BTN_ORDER)
    builder.button(text=BTN_STATUS)
    builder.button(text=BTN_LOCATION)
    builder.button(text=BTN_PROFILE)
    builder.button(text=BTN_CANCEL_ORDER)
    builder.adjust(1, 2, 2)
    return builder.as_markup(resize_keyboard=True, input_field_placeholder="Menyudan tanlang")


def contact_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_SEND_CONTACT, request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def skip_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_SKIP)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def regions_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for index, region in enumerate(REGIONS):
        builder.button(text=region, callback_data=RegionCallback(index=index))
    builder.adjust(2)
    return builder.as_markup()


def registration_confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Tasdiqlash", callback_data=RegistrationConfirmCallback(action="ok"))
    builder.button(
        text="🔄 Qaytadan kiritish", callback_data=RegistrationConfirmCallback(action="restart")
    )
    builder.adjust(1)
    return builder.as_markup()


def cancel_order_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Ha, bekor qilish", callback_data=CancelOrderCallback(action="yes"))
    builder.button(text="Yo'q", callback_data=CancelOrderCallback(action="no"))
    builder.adjust(2)
    return builder.as_markup()


def profile_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Ma'lumotlarni yangilash", callback_data=ProfileCallback(action="edit"))
    return builder.as_markup()

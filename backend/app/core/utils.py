"""Matn, manzil va telefon raqamni normallashtirish yordamchilari."""

import re

# O'zbek lotin yozuvidagi turli apostrof belgilarini bitta ko'rinishga keltiramiz:
# "G'ishtli", "Gʻishtli", "G’ishtli" -> bitta xonadon/mahalla deb hisoblanadi.
_APOSTROPHES = re.compile(r"[ʻʼ’‘`´']")
_SPACES = re.compile(r"\s+")
_NON_DIGITS = re.compile(r"\D")

KEY_SEPARATOR = "|"


def clean_text(value: str) -> str:
    """Ko'rsatish uchun: ortiqcha bo'shliqlarni olib tashlaydi, apostrofni bir xillashtiradi."""
    return _SPACES.sub(" ", _APOSTROPHES.sub("'", value.strip()))


def normalize_text(value: str) -> str:
    """Taqqoslash uchun kalit: kichik harf + tozalangan matn."""
    return clean_text(value).lower().replace(KEY_SEPARATOR, " ")


def build_mahalla_key(region: str, district: str, mahalla: str) -> str:
    return KEY_SEPARATOR.join(normalize_text(part) for part in (region, district, mahalla))


def build_household_key(
    region: str, district: str, mahalla: str, street: str, house_number: str
) -> str:
    return KEY_SEPARATOR.join(
        (
            build_mahalla_key(region, district, mahalla),
            normalize_text(street),
            normalize_text(house_number).replace(" ", ""),
        )
    )


def normalize_phone(raw: str) -> str:
    """Telefon raqamni +998XXXXXXXXX ko'rinishiga keltiradi."""
    digits = _NON_DIGITS.sub("", raw)
    if len(digits) == 9:
        digits = "998" + digits
    if len(digits) != 12 or not digits.startswith("998"):
        raise ValueError("Telefon raqam +998XXXXXXXXX formatida bo'lishi kerak")
    return "+" + digits


def normalize_car_number(raw: str) -> str:
    """'01 a 123 bc' -> '01A123BC'."""
    return re.sub(r"[\s-]", "", raw).upper()

"""Vaqt bilan ishlash: bazada UTC, foydalanuvchiga Toshkent vaqti."""

import datetime as dt

from app.core.config import settings


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def local_now() -> dt.datetime:
    return dt.datetime.now(settings.tz)


def local_today() -> dt.date:
    return local_now().date()


def local_day_start_utc(day: dt.date | None = None) -> dt.datetime:
    """Mahalliy kun boshlanishini (00:00) UTC'da qaytaradi."""
    target = day or local_today()
    return dt.datetime.combine(target, dt.time.min, tzinfo=settings.tz).astimezone(dt.UTC)


def fmt_dt(value: dt.datetime) -> str:
    return value.astimezone(settings.tz).strftime("%d.%m.%Y %H:%M")


def fmt_date(value: dt.date) -> str:
    return value.strftime("%d.%m.%Y")

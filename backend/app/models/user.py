import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.order import Order


class User(Base):
    """Aholi (gaz iste'molchisi). Telegram bot orqali ro'yxatdan o'tadi."""

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_phone_number", "phone_number"),
        Index("ix_users_mahalla_key", "mahalla_key"),
        Index("ix_users_household_key", "household_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    full_name: Mapped[str] = mapped_column(String(150))
    phone_number: Mapped[str] = mapped_column(String(20))
    region: Mapped[str] = mapped_column(String(64))
    district: Mapped[str] = mapped_column(String(100))
    mahalla: Mapped[str] = mapped_column(String(150))
    street: Mapped[str] = mapped_column(String(150))
    house_number: Mapped[str] = mapped_column(String(20))
    lpg_card_id: Mapped[str | None] = mapped_column(String(32))
    # Normallashtirilgan kalitlar: "region|district|mahalla" va "...|street|house".
    # Navbat va antifrod tekshiruvlari aynan shu kalitlar bo'yicha ishlaydi.
    mahalla_key: Mapped[str] = mapped_column(Text)
    household_key: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )

    orders: Mapped[list["Order"]] = relationship(back_populates="user", lazy="raise_on_sql")

    def __repr__(self) -> str:
        return f"User(id={self.id}, telegram_id={self.telegram_id})"

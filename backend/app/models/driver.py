import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.delivery_route import DeliveryRoute


class Driver(Base):
    """Gaz yetkazuvchi haydovchi / ta'minotchi mashinasi."""

    __tablename__ = "drivers"
    __table_args__ = (CheckConstraint("capacity > 0", name="capacity_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(150))
    phone_number: Mapped[str] = mapped_column(String(20), unique=True)
    car_number: Mapped[str] = mapped_column(String(20), unique=True)
    capacity: Mapped[int] = mapped_column(Integer)  # mashinaga sig'adigan balonlar soni
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    last_lat: Mapped[float | None] = mapped_column(Float)
    last_lon: Mapped[float | None] = mapped_column(Float)
    # Oxirgi GPS koordinata kelgan vaqt.
    updated_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )

    routes: Mapped[list["DeliveryRoute"]] = relationship(
        back_populates="driver", lazy="raise_on_sql"
    )
    locations: Mapped[list["DriverLocation"]] = relationship(
        back_populates="driver", lazy="raise_on_sql", passive_deletes=True
    )


class DriverLocation(Base):
    """GPS tarixi: mashina harakatini monitoring qilish va keyingi tahlil uchun."""

    __tablename__ = "driver_locations"
    __table_args__ = (
        Index("ix_driver_locations_driver_id_recorded_at", "driver_id", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id", ondelete="CASCADE"))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    speed: Mapped[float | None] = mapped_column(Float)  # km/soat, ixtiyoriy
    recorded_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )

    driver: Mapped["Driver"] = relationship(back_populates="locations", lazy="raise_on_sql")

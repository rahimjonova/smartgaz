import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import RouteStatus
from app.core.time import utc_now
from app.db.base import Base
from app.db.types import pg_enum

if TYPE_CHECKING:
    from app.models.driver import Driver
    from app.models.order import Order


class DeliveryRoute(Base):
    """Kunlik marshrut: bitta haydovchi, bitta mahalla, ajratilgan balonlar soni."""

    __tablename__ = "delivery_routes"
    __table_args__ = (
        UniqueConstraint(
            "driver_id", "date", "mahalla_key", name="uq_delivery_routes_driver_date_mahalla"
        ),
        Index("ix_delivery_routes_date_mahalla_key", "date", "mahalla_key"),
        CheckConstraint("allocated_cylinders > 0", name="allocated_positive"),
        CheckConstraint("delivered_count >= 0", name="delivered_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id", ondelete="RESTRICT"))
    region: Mapped[str] = mapped_column(String(64))
    district: Mapped[str] = mapped_column(String(100))
    mahalla_name: Mapped[str] = mapped_column(String(150))
    mahalla_key: Mapped[str] = mapped_column(Text)
    allocated_cylinders: Mapped[int] = mapped_column(Integer)
    delivered_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    status: Mapped[RouteStatus] = mapped_column(
        pg_enum(RouteStatus, "route_status"),
        default=RouteStatus.PLANNED,
        server_default=RouteStatus.PLANNED.value,
    )
    date: Mapped[dt.date] = mapped_column(Date)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    driver: Mapped["Driver"] = relationship(back_populates="routes", lazy="raise_on_sql")
    orders: Mapped[list["Order"]] = relationship(back_populates="route", lazy="raise_on_sql")

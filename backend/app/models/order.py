import datetime as dt
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import OrderStatus, PaymentType
from app.core.time import utc_now
from app.db.base import Base
from app.db.types import pg_enum

if TYPE_CHECKING:
    from app.models.delivery_route import DeliveryRoute
    from app.models.user import User

ACTIVE_STATUS_SQL = "status IN ('PENDING', 'APPROVED', 'ON_WAY')"


class Order(Base):
    """Gaz balonga buyurtma (navbat)."""

    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_user_id", "user_id"),
        Index("ix_orders_route_id", "route_id"),
        Index("ix_orders_status_requested_at", "status", "requested_at"),
        # Bitta foydalanuvchida bir vaqtda faqat bitta faol buyurtma (DB darajasidagi kafolat).
        Index(
            "uq_orders_user_active",
            "user_id",
            unique=True,
            postgresql_where=text(ACTIVE_STATUS_SQL),
        ),
        CheckConstraint("price >= 0", name="price_non_negative"),
        CheckConstraint("queue_number > 0", name="queue_number_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    route_id: Mapped[int | None] = mapped_column(
        ForeignKey("delivery_routes.id", ondelete="SET NULL")
    )
    status: Mapped[OrderStatus] = mapped_column(
        pg_enum(OrderStatus, "order_status"),
        default=OrderStatus.PENDING,
        server_default=OrderStatus.PENDING.value,
    )
    # Mahalla ichidagi tartib raqami (FIFO). Har bir mahalla uchun alohida o'sib boradi.
    queue_number: Mapped[int] = mapped_column(Integer)
    requested_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )
    delivered_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    payment_type: Mapped[PaymentType] = mapped_column(
        pg_enum(PaymentType, "payment_type"),
        default=PaymentType.CASH,
        server_default=PaymentType.CASH.value,
    )

    user: Mapped["User"] = relationship(back_populates="orders", lazy="raise_on_sql")
    route: Mapped["DeliveryRoute | None"] = relationship(
        back_populates="orders", lazy="raise_on_sql"
    )

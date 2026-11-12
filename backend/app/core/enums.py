"""Domen darajasidagi enumlar (SQLAlchemy va Pydantic'dan mustaqil)."""

from enum import StrEnum


class OrderStatus(StrEnum):
    PENDING = "PENDING"  # navbatda
    APPROVED = "APPROVED"  # marshrutga kiritildi (balon band qilindi)
    ON_WAY = "ON_WAY"  # mashina yo'lda
    DELIVERED = "DELIVERED"  # topshirildi
    CANCELLED = "CANCELLED"  # bekor qilindi


class PaymentType(StrEnum):
    CASH = "CASH"
    ONLINE = "ONLINE"


class RouteStatus(StrEnum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# Faol (yakunlanmagan) buyurtma holatlari: navbatda turgan deb hisoblanadi.
ACTIVE_ORDER_STATUSES: tuple[OrderStatus, ...] = (
    OrderStatus.PENDING,
    OrderStatus.APPROVED,
    OrderStatus.ON_WAY,
)

OPEN_ROUTE_STATUSES: tuple[RouteStatus, ...] = (
    RouteStatus.PLANNED,
    RouteStatus.IN_PROGRESS,
)

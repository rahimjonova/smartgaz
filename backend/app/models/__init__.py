"""Barcha modellarni bir joyda ro'yxatdan o'tkazish (Alembic metadata uchun ham)."""

from app.core.enums import OrderStatus, PaymentType, RouteStatus
from app.db.base import Base
from app.models.delivery_route import DeliveryRoute
from app.models.driver import Driver, DriverLocation
from app.models.order import Order
from app.models.user import User

__all__ = [
    "Base",
    "DeliveryRoute",
    "Driver",
    "DriverLocation",
    "Order",
    "OrderStatus",
    "PaymentType",
    "RouteStatus",
    "User",
]

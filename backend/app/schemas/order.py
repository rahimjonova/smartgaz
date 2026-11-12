import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.enums import OrderStatus, PaymentType
from app.schemas.common import ORMModel
from app.schemas.user import AddressIn


class OrderCreate(BaseModel):
    user_id: int = Field(gt=0)
    payment_type: PaymentType = PaymentType.CASH


class OrderCancel(BaseModel):
    user_id: int = Field(gt=0)


class OrderComplete(BaseModel):
    driver_id: int = Field(gt=0)
    payment_type: PaymentType | None = None


class OrderCompleteByAddress(AddressIn):
    driver_id: int = Field(gt=0)
    payment_type: PaymentType | None = None


class OrderOut(ORMModel):
    id: int
    user_id: int
    route_id: int | None
    status: OrderStatus
    queue_number: int
    requested_at: dt.datetime
    delivered_at: dt.datetime | None
    price: Decimal
    payment_type: PaymentType


class QueueStatusOut(BaseModel):
    user_id: int
    has_active_order: bool
    order: OrderOut | None = None
    # Mahalladagi joriy o'rin (1 = birinchi navbatda).
    position: int | None = None
    total_in_queue: int = 0
    estimated_delivery_date: dt.date | None = None
    last_delivered_at: dt.datetime | None = None
    next_order_allowed_at: dt.datetime | None = None

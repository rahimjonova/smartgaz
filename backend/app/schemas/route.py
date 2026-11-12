import datetime as dt

from pydantic import BaseModel, Field, field_validator

from app.core.enums import OrderStatus, RouteStatus
from app.core.utils import clean_text
from app.schemas.common import DistrictStr, MahallaStr, ORMModel, RegionStr


class RouteCreate(BaseModel):
    driver_id: int = Field(gt=0)
    region: RegionStr
    district: DistrictStr
    mahalla_name: MahallaStr
    allocated_cylinders: int = Field(gt=0, le=1000)
    date: dt.date | None = None  # berilmasa — bugun (Toshkent vaqti)

    @field_validator("region", "district", "mahalla_name")
    @classmethod
    def _clean(cls, value: str) -> str:
        return clean_text(value)


class RouteAction(BaseModel):
    driver_id: int = Field(gt=0)


class RouteOut(ORMModel):
    id: int
    driver_id: int
    region: str
    district: str
    mahalla_name: str
    allocated_cylinders: int
    delivered_count: int
    status: RouteStatus
    date: dt.date
    started_at: dt.datetime | None
    finished_at: dt.datetime | None


class RouteHouseholdOut(BaseModel):
    order_id: int
    queue_number: int
    status: OrderStatus
    user_id: int
    full_name: str
    phone_number: str
    street: str
    house_number: str
    lpg_card_id: str | None
    requested_at: dt.datetime


class RouteDetailOut(RouteOut):
    remaining_cylinders: int
    households: list[RouteHouseholdOut] = Field(default_factory=list)

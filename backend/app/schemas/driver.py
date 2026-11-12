import datetime as dt

from pydantic import BaseModel, Field, field_validator

from app.core.utils import clean_text, normalize_car_number, normalize_phone
from app.schemas.common import FullNameStr, ORMModel


class DriverCreate(BaseModel):
    full_name: FullNameStr
    phone_number: str
    car_number: str = Field(min_length=4, max_length=20)
    capacity: int = Field(gt=0, le=1000)

    @field_validator("full_name")
    @classmethod
    def _name(cls, value: str) -> str:
        return clean_text(value)

    @field_validator("phone_number")
    @classmethod
    def _phone(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator("car_number")
    @classmethod
    def _car(cls, value: str) -> str:
        return normalize_car_number(value)


class DriverUpdate(BaseModel):
    is_active: bool | None = None
    capacity: int | None = Field(default=None, gt=0, le=1000)


class DriverOut(ORMModel):
    id: int
    full_name: str
    phone_number: str
    car_number: str
    capacity: int
    is_active: bool
    last_lat: float | None
    last_lon: float | None
    updated_at: dt.datetime | None

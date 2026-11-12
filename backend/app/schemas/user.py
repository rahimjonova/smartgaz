import datetime as dt

from pydantic import BaseModel, Field, field_validator

from app.core.regions import REGIONS
from app.core.utils import clean_text, normalize_phone
from app.schemas.common import (
    DistrictStr,
    FullNameStr,
    HouseStr,
    MahallaStr,
    ORMModel,
    RegionStr,
    StreetStr,
)


class AddressIn(BaseModel):
    region: RegionStr
    district: DistrictStr
    mahalla: MahallaStr
    street: StreetStr
    house_number: HouseStr

    @field_validator("region", "district", "mahalla", "street", "house_number")
    @classmethod
    def _clean(cls, value: str) -> str:
        return clean_text(value)


class UserRegister(AddressIn):
    telegram_id: int = Field(gt=0)
    full_name: FullNameStr
    phone_number: str
    lpg_card_id: str | None = Field(default=None, pattern=r"^[A-Z0-9-]{4,32}$")

    @field_validator("full_name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        return clean_text(value)

    @field_validator("phone_number")
    @classmethod
    def _phone(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator("region")
    @classmethod
    def _region_known(cls, value: str) -> str:
        if value not in REGIONS:
            raise ValueError("Noma'lum viloyat")
        return value

    @field_validator("lpg_card_id", mode="before")
    @classmethod
    def _card_upper(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip().upper().replace(" ", "")
            return stripped or None
        return value


class UserOut(ORMModel):
    id: int
    telegram_id: int
    full_name: str
    phone_number: str
    region: str
    district: str
    mahalla: str
    street: str
    house_number: str
    lpg_card_id: str | None
    created_at: dt.datetime

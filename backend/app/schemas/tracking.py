import datetime as dt

from pydantic import AwareDatetime, BaseModel, Field


class LocationUpdate(BaseModel):
    driver_id: int = Field(gt=0)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    speed: float | None = Field(default=None, ge=0, le=300)
    # Qurilmadagi o'lchov vaqti (timezone bilan). Berilmasa server vaqti olinadi.
    recorded_at: AwareDatetime | None = None


class LocationAck(BaseModel):
    driver_id: int
    lat: float
    lon: float
    updated_at: dt.datetime
    next_update_in_seconds: int


class DriverLocationOut(BaseModel):
    driver_id: int
    full_name: str
    car_number: str
    lat: float | None
    lon: float | None
    updated_at: dt.datetime | None
    is_online: bool
    map_url: str | None

import datetime as dt

from pydantic import BaseModel, Field


class StatsCounters(BaseModel):
    households: int = 0  # ro'yxatdan o'tgan xonadonlar
    total_demand: int = 0  # jami ehtiyoj = faol navbatdagi buyurtmalar
    pending: int = 0  # kutayotgan navbatlar
    in_delivery: int = 0  # marshrutga kiritilgan / yo'lda
    delivered_total: int = 0  # jami tarqatilgan balonlar
    delivered_today: int = 0

    def add(self, other: "StatsCounters") -> None:
        for name in type(self).model_fields:
            setattr(self, name, getattr(self, name) + getattr(other, name))


class MahallaStats(StatsCounters):
    region: str
    district: str
    mahalla: str


class DistrictStats(BaseModel):
    region: str
    district: str
    totals: StatsCounters
    mahallas: list[MahallaStats] = Field(default_factory=list)


class StatsOut(BaseModel):
    generated_at: dt.datetime
    totals: StatsCounters
    active_drivers: int
    routes_today: int
    districts: list[DistrictStats]

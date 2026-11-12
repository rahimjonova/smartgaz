"""Admin/dispecher statistikasi: viloyat → tuman → mahalla kesimida."""

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ACTIVE_ORDER_STATUSES, OrderStatus
from app.core.time import local_day_start_utc, local_today, utc_now
from app.core.utils import KEY_SEPARATOR, normalize_text
from app.models import DeliveryRoute, Driver, Order, User
from app.schemas.stats import DistrictStats, MahallaStats, StatsCounters, StatsOut


async def get_stats(
    session: AsyncSession, region: str | None = None, district: str | None = None
) -> StatsOut:
    day_start = local_day_start_utc()
    region_part = func.split_part(User.mahalla_key, KEY_SEPARATOR, 1)
    district_part = func.split_part(User.mahalla_key, KEY_SEPARATOR, 2)

    stmt = (
        select(
            User.mahalla_key,
            func.min(User.region).label("region"),
            func.min(User.district).label("district"),
            func.min(User.mahalla).label("mahalla"),
            func.count(func.distinct(User.household_key)).label("households"),
            func.count(Order.id)
            .filter(Order.status.in_(ACTIVE_ORDER_STATUSES))
            .label("total_demand"),
            func.count(Order.id).filter(Order.status == OrderStatus.PENDING).label("pending"),
            func.count(Order.id)
            .filter(Order.status.in_((OrderStatus.APPROVED, OrderStatus.ON_WAY)))
            .label("in_delivery"),
            func.count(Order.id)
            .filter(Order.status == OrderStatus.DELIVERED)
            .label("delivered_total"),
            func.count(Order.id)
            .filter(and_(Order.status == OrderStatus.DELIVERED, Order.delivered_at >= day_start))
            .label("delivered_today"),
        )
        .select_from(User)
        .outerjoin(Order, Order.user_id == User.id)
        .group_by(User.mahalla_key)
        .order_by(User.mahalla_key)
    )
    if region:
        stmt = stmt.where(region_part == normalize_text(region))
    if district:
        stmt = stmt.where(district_part == normalize_text(district))

    rows = (await session.execute(stmt)).mappings().all()

    totals = StatsCounters()
    districts: dict[tuple[str, str], DistrictStats] = {}
    for row in rows:
        mahalla_stats = MahallaStats(
            region=row["region"],
            district=row["district"],
            mahalla=row["mahalla"],
            households=row["households"],
            total_demand=row["total_demand"],
            pending=row["pending"],
            in_delivery=row["in_delivery"],
            delivered_total=row["delivered_total"],
            delivered_today=row["delivered_today"],
        )
        region_key, district_key, _ = str(row["mahalla_key"]).split(KEY_SEPARATOR, 2)
        bucket = districts.get((region_key, district_key))
        if bucket is None:
            bucket = DistrictStats(
                region=mahalla_stats.region,
                district=mahalla_stats.district,
                totals=StatsCounters(),
            )
            districts[(region_key, district_key)] = bucket
        bucket.mahallas.append(mahalla_stats)
        counters = StatsCounters.model_validate(
            mahalla_stats.model_dump(include=set(StatsCounters.model_fields))
        )
        bucket.totals.add(counters)
        totals.add(counters)

    active_drivers = await session.scalar(
        select(func.count(Driver.id)).where(Driver.is_active.is_(True))
    )
    routes_today = await session.scalar(
        select(func.count(DeliveryRoute.id)).where(DeliveryRoute.date == local_today())
    )
    return StatsOut(
        generated_at=utc_now(),
        totals=totals,
        active_drivers=int(active_drivers or 0),
        routes_today=int(routes_today or 0),
        districts=list(districts.values()),
    )

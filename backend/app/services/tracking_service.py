"""GPS monitoring: haydovchi koordinatalari va aholiga mashina joylashuvi."""

import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import RouteStatus
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.time import local_today, utc_now
from app.models import DeliveryRoute, Driver, DriverLocation, User
from app.schemas.tracking import DriverLocationOut, LocationUpdate
from app.services.order_service import get_household_active_order

_MAX_CLOCK_SKEW = dt.timedelta(minutes=2)


def map_url(lat: float, lon: float) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={lat:.6f},{lon:.6f}"


async def update_location(session: AsyncSession, data: LocationUpdate) -> Driver:
    driver = await session.get(Driver, data.driver_id)
    if driver is None:
        raise NotFoundError("Haydovchi topilmadi")
    if not driver.is_active:
        raise PermissionDeniedError("Haydovchi faol emas")

    now = utc_now()
    recorded_at = data.recorded_at.astimezone(dt.UTC) if data.recorded_at else now
    if recorded_at > now + _MAX_CLOCK_SKEW:  # qurilma soati noto'g'ri bo'lsa
        recorded_at = now

    session.add(
        DriverLocation(
            driver_id=driver.id,
            lat=data.lat,
            lon=data.lon,
            speed=data.speed,
            recorded_at=recorded_at,
        )
    )
    # Kechikib kelgan (eski) nuqta oxirgi joylashuvni bosib ketmasin.
    if driver.updated_at is None or recorded_at >= driver.updated_at:
        driver.last_lat = data.lat
        driver.last_lon = data.lon
        driver.updated_at = recorded_at
    await session.commit()
    return driver


def to_location_out(driver: Driver) -> DriverLocationOut:
    is_online = driver.updated_at is not None and (
        (utc_now() - driver.updated_at).total_seconds() <= settings.DRIVER_ONLINE_THRESHOLD_SECONDS
    )
    has_coords = driver.last_lat is not None and driver.last_lon is not None
    return DriverLocationOut(
        driver_id=driver.id,
        full_name=driver.full_name,
        car_number=driver.car_number,
        lat=driver.last_lat,
        lon=driver.last_lon,
        updated_at=driver.updated_at,
        is_online=is_online,
        map_url=map_url(driver.last_lat, driver.last_lon)  # type: ignore[arg-type]
        if has_coords
        else None,
    )


async def get_driver_location(session: AsyncSession, driver_id: int) -> DriverLocationOut:
    driver = await session.get(Driver, driver_id)
    if driver is None:
        raise NotFoundError("Haydovchi topilmadi")
    return to_location_out(driver)


async def get_driver_location_for_user(
    session: AsyncSession, user_id: int
) -> DriverLocationOut | None:
    """Foydalanuvchiga tegishli mashina: avval o'z buyurtmasining marshruti,
    bo'lmasa — mahallasida bugun yo'lga chiqqan marshrut."""
    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundError("Foydalanuvchi topilmadi")

    route: DeliveryRoute | None = None
    order = await get_household_active_order(session, user.household_key)
    if order is not None and order.route_id is not None:
        route = await session.get(DeliveryRoute, order.route_id)

    if route is None or route.status != RouteStatus.IN_PROGRESS:
        route = await session.scalar(
            select(DeliveryRoute)
            .where(
                DeliveryRoute.mahalla_key == user.mahalla_key,
                DeliveryRoute.date == local_today(),
                DeliveryRoute.status == RouteStatus.IN_PROGRESS,
            )
            .order_by(DeliveryRoute.started_at.desc())
            .limit(1)
        )
    if route is None:
        return None

    driver = await session.get(Driver, route.driver_id)
    return to_location_out(driver) if driver is not None else None

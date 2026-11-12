from typing import Annotated

from fastapi import APIRouter, Path

from app.api.deps import DriverAccess, ServiceAccess, ServiceOrDriverAccess, SessionDep
from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.time import utc_now
from app.schemas.tracking import DriverLocationOut, LocationAck, LocationUpdate
from app.services import tracking_service

router = APIRouter(prefix="/tracking", tags=["Tracking — GPS"])


@router.post(
    "/update-location",
    response_model=LocationAck,
    dependencies=[DriverAccess],
    summary="Haydovchi GPS koordinatasini yuborish (har 30 soniyada)",
)
async def update_location(payload: LocationUpdate, session: SessionDep) -> LocationAck:
    driver = await tracking_service.update_location(session, payload)
    return LocationAck(
        driver_id=driver.id,
        lat=payload.lat,
        lon=payload.lon,
        updated_at=driver.updated_at or utc_now(),
        next_update_in_seconds=settings.GPS_UPDATE_INTERVAL_SECONDS,
    )


@router.get(
    "/driver/{driver_id}",
    response_model=DriverLocationOut,
    dependencies=[ServiceOrDriverAccess],
    summary="Haydovchining oxirgi joylashuvi",
)
async def driver_location(
    driver_id: Annotated[int, Path(gt=0)], session: SessionDep
) -> DriverLocationOut:
    return await tracking_service.get_driver_location(session, driver_id)


@router.get(
    "/user/{user_id}",
    response_model=DriverLocationOut,
    dependencies=[ServiceAccess],
    summary="Foydalanuvchi mahallasiga kelayotgan mashina joylashuvi",
)
async def user_driver_location(
    user_id: Annotated[int, Path(gt=0)], session: SessionDep
) -> DriverLocationOut:
    location = await tracking_service.get_driver_location_for_user(session, user_id)
    if location is None:
        raise NotFoundError("Hozircha mahallangizga yo'lga chiqqan mashina yo'q")
    return location

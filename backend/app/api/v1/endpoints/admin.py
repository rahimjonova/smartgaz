from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.deps import AdminOnly, SessionDep
from app.schemas.driver import DriverCreate, DriverOut, DriverUpdate
from app.schemas.route import RouteCreate, RouteDetailOut
from app.schemas.stats import StatsOut
from app.services import driver_service, route_service, stats_service

router = APIRouter(prefix="/admin", tags=["Admin — dispecher"], dependencies=[AdminOnly])


@router.get(
    "/stats",
    response_model=StatsOut,
    summary="Mahalla va tumanlar bo'yicha ehtiyoj, navbat va tarqatilgan balonlar",
)
async def stats(
    session: SessionDep,
    region: Annotated[str | None, Query(max_length=64)] = None,
    district: Annotated[str | None, Query(max_length=100)] = None,
) -> StatsOut:
    return await stats_service.get_stats(session, region=region, district=district)


@router.post("/drivers", response_model=DriverOut, status_code=status.HTTP_201_CREATED)
async def create_driver(payload: DriverCreate, session: SessionDep) -> DriverOut:
    return DriverOut.model_validate(await driver_service.create_driver(session, payload))


@router.get("/drivers", response_model=list[DriverOut])
async def list_drivers(session: SessionDep, only_active: bool = False) -> list[DriverOut]:
    drivers = await driver_service.list_drivers(session, only_active=only_active)
    return [DriverOut.model_validate(driver) for driver in drivers]


@router.patch("/drivers/{driver_id}", response_model=DriverOut)
async def update_driver(
    driver_id: Annotated[int, Path(gt=0)], payload: DriverUpdate, session: SessionDep
) -> DriverOut:
    driver = await driver_service.update_driver(session, driver_id, payload)
    return DriverOut.model_validate(driver)


@router.post(
    "/routes",
    response_model=RouteDetailOut,
    status_code=status.HTTP_201_CREATED,
    summary="Marshrut yaratish: mahalladagi navbat FIFO bo'yicha band qilinadi",
)
async def create_route(payload: RouteCreate, session: SessionDep) -> RouteDetailOut:
    route = await route_service.create_route(session, payload)
    return await route_service.build_route_detail(session, route)

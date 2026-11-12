from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Path

from app.api.deps import DriverAccess, NotifierDep, SessionDep
from app.schemas.route import RouteAction, RouteDetailOut, RouteOut
from app.services import route_service

router = APIRouter(
    prefix="/routes", tags=["Routes — haydovchi marshruti"], dependencies=[DriverAccess]
)

ON_WAY_TEXT = (
    "🚚 Gaz mashinasi mahallangizga yo'lga chiqdi!\n"
    "Joylashuvni ko'rish uchun «🚚 Mashina lokatsiyasi» tugmasini bosing."
)


@router.get(
    "/today/{driver_id}",
    response_model=list[RouteDetailOut],
    summary="Bugungi marshrut: mahalladagi navbatdagi xonadonlar (FIFO)",
)
async def today_routes(
    driver_id: Annotated[int, Path(gt=0)], session: SessionDep
) -> list[RouteDetailOut]:
    return await route_service.get_today_routes(session, driver_id)


@router.post(
    "/{route_id}/start",
    response_model=RouteDetailOut,
    summary="Marshrutni boshlash (xonadonlarga «mashina yo'lda» xabari ketadi)",
)
async def start_route(
    route_id: Annotated[int, Path(gt=0)],
    payload: RouteAction,
    session: SessionDep,
    notifier: NotifierDep,
    background_tasks: BackgroundTasks,
) -> RouteDetailOut:
    result = await route_service.start_route(session, route_id, payload.driver_id)
    if result.notify_telegram_ids:
        background_tasks.add_task(notifier.broadcast, result.notify_telegram_ids, ON_WAY_TEXT)
    return await route_service.build_route_detail(session, result.route)


@router.post(
    "/{route_id}/finish",
    response_model=RouteOut,
    summary="Marshrutni yakunlash (topshirilmaganlar navbatga qaytadi)",
)
async def finish_route(
    route_id: Annotated[int, Path(gt=0)], payload: RouteAction, session: SessionDep
) -> RouteOut:
    route = await route_service.finish_route(session, route_id, payload.driver_id)
    return RouteOut.model_validate(route)

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Path, status

from app.api.deps import DriverAccess, NotifierDep, ServiceAccess, SessionDep
from app.core.time import fmt_dt
from app.schemas.order import (
    OrderCancel,
    OrderComplete,
    OrderCompleteByAddress,
    OrderCreate,
    OrderOut,
    QueueStatusOut,
)
from app.services import order_service
from app.services.order_service import DeliveryResult

router = APIRouter(prefix="/orders", tags=["Orders — navbat"])


def _delivered_text(result: DeliveryResult) -> str:
    order = result.order
    when = fmt_dt(order.delivered_at) if order.delivered_at else ""
    price = f"{order.price:,.0f}".replace(",", " ")
    return f"✅ Gaz baloni topshirildi.\nBuyurtma: #{order.id}\nVaqt: {when}\nNarx: {price} so'm"


@router.post(
    "/create",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[ServiceAccess],
    summary="Gazga navbatga turish",
    responses={409: {"description": "Siz yaqinda gaz olgansiz yoki navbatdasiz"}},
)
async def create_order(payload: OrderCreate, session: SessionDep) -> OrderOut:
    order = await order_service.create_order(session, payload.user_id, payload.payment_type)
    return OrderOut.model_validate(order)


@router.get(
    "/queue-status/{user_id}",
    response_model=QueueStatusOut,
    dependencies=[ServiceAccess],
    summary="Navbat holati: mahalladagi o'rin va taxminiy sana",
)
async def queue_status(user_id: Annotated[int, Path(gt=0)], session: SessionDep) -> QueueStatusOut:
    return await order_service.get_queue_status(session, user_id)


@router.post(
    "/cancel",
    response_model=OrderOut,
    dependencies=[ServiceAccess],
    summary="Navbatni bekor qilish (mashina yo'lga chiqmagan bo'lsa)",
)
async def cancel_order(payload: OrderCancel, session: SessionDep) -> OrderOut:
    order = await order_service.cancel_order(session, payload.user_id)
    return OrderOut.model_validate(order)


@router.post(
    "/complete-by-address",
    response_model=OrderOut,
    dependencies=[DriverAccess],
    summary="Balon topshirilganini xonadon manzili bo'yicha qayd etish",
)
async def complete_by_address(
    payload: OrderCompleteByAddress,
    session: SessionDep,
    notifier: NotifierDep,
    background_tasks: BackgroundTasks,
) -> OrderOut:
    result = await order_service.complete_order_by_address(
        session, payload.driver_id, payload, payload.payment_type
    )
    background_tasks.add_task(notifier.send, result.telegram_id, _delivered_text(result))
    return OrderOut.model_validate(result.order)


@router.post(
    "/{order_id}/complete",
    response_model=OrderOut,
    dependencies=[DriverAccess],
    summary="Balon topshirilganini buyurtma ID bo'yicha qayd etish (DELIVERED)",
)
async def complete_order(
    order_id: Annotated[int, Path(gt=0)],
    payload: OrderComplete,
    session: SessionDep,
    notifier: NotifierDep,
    background_tasks: BackgroundTasks,
) -> OrderOut:
    result = await order_service.complete_order(
        session, order_id, payload.driver_id, payload.payment_type
    )
    background_tasks.add_task(notifier.send, result.telegram_id, _delivered_text(result))
    return OrderOut.model_validate(result.order)

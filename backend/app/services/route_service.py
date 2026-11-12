"""Marshrutlar: yaratish (FIFO bo'yicha balon band qilish), boshlash, yakunlash."""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ACTIVE_ORDER_STATUSES, OPEN_ROUTE_STATUSES, OrderStatus, RouteStatus
from app.core.exceptions import (
    DomainError,
    InvalidStateError,
    NotFoundError,
    PermissionDeniedError,
    ValidationFailedError,
)
from app.core.time import local_today, utc_now
from app.core.utils import build_mahalla_key
from app.models import DeliveryRoute, Driver, Order, User
from app.schemas.route import RouteCreate, RouteDetailOut, RouteHouseholdOut, RouteOut
from app.services.locks import advisory_xact_lock


@dataclass(slots=True)
class RouteStartResult:
    route: DeliveryRoute
    notify_telegram_ids: list[int]


async def create_route(session: AsyncSession, data: RouteCreate) -> DeliveryRoute:
    """Marshrut yaratadi va mahalladagi navbatni FIFO tartibida band qiladi (PENDING -> APPROVED)."""
    try:
        driver = await session.get(Driver, data.driver_id)
        if driver is None or not driver.is_active:
            raise NotFoundError("Haydovchi topilmadi yoki faol emas")
        if data.allocated_cylinders > driver.capacity:
            raise ValidationFailedError(
                f"Ajratilgan balonlar soni mashina sig'imidan ({driver.capacity}) oshmasligi kerak"
            )

        mahalla_key = build_mahalla_key(data.region, data.district, data.mahalla_name)
        await advisory_xact_lock(session, mahalla_key)

        route = DeliveryRoute(
            driver_id=driver.id,
            region=data.region,
            district=data.district,
            mahalla_name=data.mahalla_name,
            mahalla_key=mahalla_key,
            allocated_cylinders=data.allocated_cylinders,
            delivered_count=0,
            status=RouteStatus.PLANNED,
            date=data.date or local_today(),
        )
        session.add(route)
        await session.flush()

        order_ids = (
            await session.scalars(
                select(Order.id)
                .join(User, User.id == Order.user_id)
                .where(
                    User.mahalla_key == mahalla_key,
                    Order.status == OrderStatus.PENDING,
                    Order.route_id.is_(None),
                )
                .order_by(Order.queue_number)
                .limit(data.allocated_cylinders)
                .with_for_update(of=Order, skip_locked=True)
            )
        ).all()
        if order_ids:
            await session.execute(
                update(Order)
                .where(Order.id.in_(order_ids))
                .values(status=OrderStatus.APPROVED, route_id=route.id)
                .execution_options(synchronize_session=False)
            )
        await session.commit()
    except DomainError:
        await session.rollback()
        raise
    except IntegrityError as exc:
        await session.rollback()
        raise InvalidStateError(
            "Bu haydovchi uchun shu sanada ushbu mahallaga marshrut allaqachon yaratilgan"
        ) from exc
    return route


async def get_route_households(session: AsyncSession, route_id: int) -> list[RouteHouseholdOut]:
    rows = (
        await session.execute(
            select(Order, User)
            .join(User, User.id == Order.user_id)
            .where(
                Order.route_id == route_id,
                Order.status.in_((*ACTIVE_ORDER_STATUSES, OrderStatus.DELIVERED)),
            )
            .order_by(Order.queue_number)
        )
    ).all()
    return [
        RouteHouseholdOut(
            order_id=order.id,
            queue_number=order.queue_number,
            status=order.status,
            user_id=user.id,
            full_name=user.full_name,
            phone_number=user.phone_number,
            street=user.street,
            house_number=user.house_number,
            lpg_card_id=user.lpg_card_id,
            requested_at=order.requested_at,
        )
        for order, user in rows
    ]


async def build_route_detail(session: AsyncSession, route: DeliveryRoute) -> RouteDetailOut:
    base = RouteOut.model_validate(route).model_dump()
    return RouteDetailOut(
        **base,
        remaining_cylinders=max(route.allocated_cylinders - route.delivered_count, 0),
        households=await get_route_households(session, route.id),
    )


async def get_today_routes(session: AsyncSession, driver_id: int) -> list[RouteDetailOut]:
    """Haydovchining bugungi marshrutlari va har biridagi xonadonlar (FIFO)."""
    if await session.get(Driver, driver_id) is None:
        raise NotFoundError("Haydovchi topilmadi")
    routes: Sequence[DeliveryRoute] = (
        await session.scalars(
            select(DeliveryRoute)
            .where(
                DeliveryRoute.driver_id == driver_id,
                DeliveryRoute.date == local_today(),
                DeliveryRoute.status.in_(OPEN_ROUTE_STATUSES),
            )
            .order_by(DeliveryRoute.id)
        )
    ).all()
    return [await build_route_detail(session, route) for route in routes]


async def _get_route_for_driver(
    session: AsyncSession, route_id: int, driver_id: int
) -> DeliveryRoute:
    route = await session.scalar(
        select(DeliveryRoute)
        .where(DeliveryRoute.id == route_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if route is None:
        raise NotFoundError("Marshrut topilmadi")
    if route.driver_id != driver_id:
        raise PermissionDeniedError("Bu marshrut boshqa haydovchiga tegishli")
    return route


async def start_route(session: AsyncSession, route_id: int, driver_id: int) -> RouteStartResult:
    """Marshrutni boshlash: APPROVED buyurtmalar ON_WAY holatiga o'tadi."""
    try:
        route = await _get_route_for_driver(session, route_id, driver_id)
        if route.status != RouteStatus.PLANNED:
            raise InvalidStateError("Faqat rejalashtirilgan marshrutni boshlash mumkin")
        route.status = RouteStatus.IN_PROGRESS
        route.started_at = utc_now()

        user_ids = (
            (
                await session.execute(
                    update(Order)
                    .where(Order.route_id == route.id, Order.status == OrderStatus.APPROVED)
                    .values(status=OrderStatus.ON_WAY)
                    .returning(Order.user_id)
                    .execution_options(synchronize_session=False)
                )
            )
            .scalars()
            .all()
        )
        telegram_ids: list[int] = []
        if user_ids:
            telegram_ids = list(
                (await session.scalars(select(User.telegram_id).where(User.id.in_(user_ids)))).all()
            )
        await session.commit()
    except DomainError:
        await session.rollback()
        raise
    return RouteStartResult(route=route, notify_telegram_ids=telegram_ids)


async def finish_route(session: AsyncSession, route_id: int, driver_id: int) -> DeliveryRoute:
    """Marshrutni yakunlash. Topshirilmay qolgan xonadonlar navbatdagi o'rnini saqlagan holda
    PENDING holatiga qaytariladi (keyingi marshrutda birinchilardan bo'lib xizmat qilinadi)."""
    try:
        route = await _get_route_for_driver(session, route_id, driver_id)
        if route.status not in OPEN_ROUTE_STATUSES:
            raise InvalidStateError("Marshrut allaqachon yakunlangan")
        await session.execute(
            update(Order)
            .where(
                Order.route_id == route.id,
                Order.status.in_((OrderStatus.APPROVED, OrderStatus.ON_WAY)),
            )
            .values(status=OrderStatus.PENDING, route_id=None)
            .execution_options(synchronize_session=False)
        )
        route.status = RouteStatus.COMPLETED
        route.finished_at = utc_now()
        await session.commit()
    except DomainError:
        await session.rollback()
        raise
    return route

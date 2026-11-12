"""Buyurtma (navbat) biznes-mantiqi: yaratish, antifrod, navbat holati, topshirish."""

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import (
    ACTIVE_ORDER_STATUSES,
    OPEN_ROUTE_STATUSES,
    OrderStatus,
    PaymentType,
)
from app.core.exceptions import (
    DomainError,
    InvalidStateError,
    NotFoundError,
    OrderNotAllowedError,
    PermissionDeniedError,
)
from app.core.time import fmt_dt, local_today, utc_now
from app.core.utils import build_household_key
from app.models import DeliveryRoute, Driver, Order, User
from app.schemas.order import OrderOut, QueueStatusOut
from app.schemas.user import AddressIn
from app.services.locks import advisory_xact_lock

ANTIFRAUD_MESSAGE = "Siz yaqinda gaz olgansiz yoki navbatdasiz"


@dataclass(slots=True)
class DeliveryResult:
    order: Order
    telegram_id: int


# ---------------------------------------------------------------- yordamchi so'rovlar


async def get_active_order(session: AsyncSession, user_id: int) -> Order | None:
    stmt = (
        select(Order)
        .where(Order.user_id == user_id, Order.status.in_(ACTIVE_ORDER_STATUSES))
        .order_by(Order.requested_at.desc())
        .limit(1)
    )
    return await session.scalar(stmt)


async def get_household_active_order(session: AsyncSession, household_key: str) -> Order | None:
    stmt = (
        select(Order)
        .join(User, User.id == Order.user_id)
        .where(User.household_key == household_key, Order.status.in_(ACTIVE_ORDER_STATUSES))
        .order_by(Order.queue_number)
        .limit(1)
    )
    return await session.scalar(stmt)


async def get_household_last_delivery(
    session: AsyncSession, household_key: str
) -> dt.datetime | None:
    stmt = (
        select(func.max(Order.delivered_at))
        .select_from(Order)
        .join(User, User.id == Order.user_id)
        .where(User.household_key == household_key, Order.status == OrderStatus.DELIVERED)
    )
    return await session.scalar(stmt)


def next_order_allowed_at(last_delivered_at: dt.datetime) -> dt.datetime:
    return last_delivered_at + dt.timedelta(days=settings.REORDER_COOLDOWN_DAYS)


async def _count_active_in_mahalla(
    session: AsyncSession, mahalla_key: str, before_queue_number: int | None = None
) -> int:
    stmt = (
        select(func.count(Order.id))
        .select_from(Order)
        .join(User, User.id == Order.user_id)
        .where(User.mahalla_key == mahalla_key, Order.status.in_(ACTIVE_ORDER_STATUSES))
    )
    if before_queue_number is not None:
        stmt = stmt.where(Order.queue_number < before_queue_number)
    return int(await session.scalar(stmt) or 0)


async def _get_user(session: AsyncSession, user_id: int) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundError("Foydalanuvchi topilmadi")
    return user


# ---------------------------------------------------------------- navbatga turish


async def create_order(
    session: AsyncSession, user_id: int, payment_type: PaymentType = PaymentType.CASH
) -> Order:
    """Yangi navbat yaratadi. Antifrod qoidalari:

    * xonadonda (shu manzildagi istalgan foydalanuvchida) faol navbat bo'lsa — rad etiladi;
    * xonadon oxirgi REORDER_COOLDOWN_DAYS (20) kun ichida balon olgan bo'lsa — rad etiladi.
    """
    try:
        user = await _get_user(session, user_id)
        # Mahalla bo'yicha lock: navbat raqami va antifrod tekshiruvi poygasiz bajariladi.
        await advisory_xact_lock(session, user.mahalla_key)

        if await get_household_active_order(session, user.household_key) is not None:
            raise OrderNotAllowedError(
                f"{ANTIFRAUD_MESSAGE}: xonadoningiz allaqachon navbatda turibdi."
            )

        last_delivery = await get_household_last_delivery(session, user.household_key)
        if last_delivery is not None:
            allowed_at = next_order_allowed_at(last_delivery)
            if allowed_at > utc_now():
                raise OrderNotAllowedError(
                    f"{ANTIFRAUD_MESSAGE}: oxirgi balon {fmt_dt(last_delivery)} da olingan. "
                    f"Keyingi navbat {fmt_dt(allowed_at)} dan keyin ochiladi."
                )

        next_queue_number = await session.scalar(
            select(func.coalesce(func.max(Order.queue_number), 0) + 1)
            .select_from(Order)
            .join(User, User.id == Order.user_id)
            .where(User.mahalla_key == user.mahalla_key)
        )
        order = Order(
            user_id=user.id,
            status=OrderStatus.PENDING,
            queue_number=int(next_queue_number or 1),
            price=settings.CYLINDER_PRICE,
            payment_type=payment_type,
            requested_at=utc_now(),
        )
        session.add(order)
        await session.commit()
    except DomainError:
        await session.rollback()
        raise
    except IntegrityError as exc:
        await session.rollback()
        raise OrderNotAllowedError(f"{ANTIFRAUD_MESSAGE}.") from exc
    return order


async def cancel_order(session: AsyncSession, user_id: int) -> Order:
    try:
        order = await session.scalar(
            select(Order)
            .where(
                Order.user_id == user_id,
                Order.status.in_((OrderStatus.PENDING, OrderStatus.APPROVED)),
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if order is None:
            active = await get_active_order(session, user_id)
            if active is not None and active.status == OrderStatus.ON_WAY:
                raise InvalidStateError("Mashina yo'lda — buyurtmani bekor qilib bo'lmaydi.")
            raise NotFoundError("Sizda faol navbat yo'q.")
        order.status = OrderStatus.CANCELLED
        await session.commit()
    except DomainError:
        await session.rollback()
        raise
    return order


# ---------------------------------------------------------------- navbat holati


async def get_queue_status(session: AsyncSession, user_id: int) -> QueueStatusOut:
    user = await _get_user(session, user_id)
    total = await _count_active_in_mahalla(session, user.mahalla_key)

    last_delivery = await get_household_last_delivery(session, user.household_key)
    allowed_at: dt.datetime | None = None
    if last_delivery is not None:
        candidate = next_order_allowed_at(last_delivery)
        allowed_at = candidate if candidate > utc_now() else None

    order = await get_household_active_order(session, user.household_key)
    if order is None:
        return QueueStatusOut(
            user_id=user.id,
            has_active_order=False,
            total_in_queue=total,
            last_delivered_at=last_delivery,
            next_order_allowed_at=allowed_at,
        )

    ahead = await _count_active_in_mahalla(
        session, user.mahalla_key, before_queue_number=order.queue_number
    )
    position = ahead + 1
    return QueueStatusOut(
        user_id=user.id,
        has_active_order=True,
        order=OrderOut.model_validate(order),
        position=position,
        total_in_queue=total,
        estimated_delivery_date=await _estimate_delivery_date(session, order, position),
        last_delivered_at=last_delivery,
        next_order_allowed_at=allowed_at,
    )


async def _estimate_delivery_date(session: AsyncSession, order: Order, position: int) -> dt.date:
    today = local_today()
    if order.status == OrderStatus.ON_WAY:
        return today
    if order.route_id is not None:
        route = await session.get(DeliveryRoute, order.route_id)
        if route is not None:
            return max(route.date, today)
    # Marshrutga hali kiritilmagan: mahallaning kunlik o'rtacha quvvati bo'yicha hisob.
    days_ahead = (position - 1) // settings.DAILY_CAPACITY_PER_MAHALLA
    return today + dt.timedelta(days=days_ahead)


# ---------------------------------------------------------------- topshirish


async def complete_order(
    session: AsyncSession,
    order_id: int,
    driver_id: int,
    payment_type: PaymentType | None = None,
) -> DeliveryResult:
    try:
        order = await session.scalar(
            select(Order)
            .where(Order.id == order_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if order is None:
            raise NotFoundError("Buyurtma topilmadi")
        return await _mark_delivered(session, order, driver_id, payment_type)
    except DomainError:
        await session.rollback()
        raise


async def complete_order_by_address(
    session: AsyncSession,
    driver_id: int,
    address: AddressIn,
    payment_type: PaymentType | None = None,
) -> DeliveryResult:
    household_key = build_household_key(
        address.region, address.district, address.mahalla, address.street, address.house_number
    )
    try:
        order = await session.scalar(
            select(Order)
            .join(User, User.id == Order.user_id)
            .where(User.household_key == household_key, Order.status.in_(ACTIVE_ORDER_STATUSES))
            .order_by(Order.queue_number)
            .limit(1)
            .with_for_update(of=Order)
            .execution_options(populate_existing=True)
        )
        if order is None:
            raise NotFoundError("Bu manzil bo'yicha faol navbat topilmadi")
        return await _mark_delivered(session, order, driver_id, payment_type)
    except DomainError:
        await session.rollback()
        raise


async def _mark_delivered(
    session: AsyncSession,
    order: Order,
    driver_id: int,
    payment_type: PaymentType | None,
) -> DeliveryResult:
    if order.status == OrderStatus.DELIVERED:
        raise InvalidStateError("Bu buyurtma allaqachon topshirilgan")
    if order.status == OrderStatus.CANCELLED:
        raise InvalidStateError("Bu buyurtma bekor qilingan")

    driver = await session.get(Driver, driver_id)
    if driver is None or not driver.is_active:
        raise NotFoundError("Haydovchi topilmadi yoki faol emas")

    user = await _get_user(session, order.user_id)

    route_stmt = select(DeliveryRoute).with_for_update().execution_options(populate_existing=True)
    if order.route_id is not None:
        route = await session.scalar(route_stmt.where(DeliveryRoute.id == order.route_id))
        if route is not None and route.driver_id != driver.id:
            raise PermissionDeniedError(
                "Bu buyurtma boshqa haydovchining marshrutiga biriktirilgan"
            )
    else:
        # Navbatdan tashqari topshirish: haydovchining shu mahalladagi bugungi marshrutiga bog'laymiz.
        route = await session.scalar(
            route_stmt.where(
                DeliveryRoute.driver_id == driver.id,
                DeliveryRoute.date == local_today(),
                DeliveryRoute.mahalla_key == user.mahalla_key,
                DeliveryRoute.status.in_(OPEN_ROUTE_STATUSES),
            ).limit(1)
        )
        if route is not None:
            order.route_id = route.id

    if route is not None:
        if route.delivered_count >= route.allocated_cylinders:
            raise InvalidStateError("Marshrut bo'yicha ajratilgan balonlar tugagan")
        route.delivered_count += 1

    order.status = OrderStatus.DELIVERED
    order.delivered_at = utc_now()
    if payment_type is not None:
        order.payment_type = payment_type

    await session.commit()
    return DeliveryResult(order=order, telegram_id=user.telegram_id)

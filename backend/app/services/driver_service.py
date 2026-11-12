from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError, NotFoundError
from app.models import Driver
from app.schemas.driver import DriverCreate, DriverUpdate


async def create_driver(session: AsyncSession, data: DriverCreate) -> Driver:
    driver = Driver(**data.model_dump(), is_active=True)
    session.add(driver)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise InvalidStateError(
            "Bu telefon raqam yoki avtomobil raqami bilan haydovchi mavjud"
        ) from exc
    return driver


async def list_drivers(session: AsyncSession, only_active: bool = False) -> Sequence[Driver]:
    stmt = select(Driver).order_by(Driver.id)
    if only_active:
        stmt = stmt.where(Driver.is_active.is_(True))
    return (await session.scalars(stmt)).all()


async def get_driver(session: AsyncSession, driver_id: int) -> Driver:
    driver = await session.get(Driver, driver_id)
    if driver is None:
        raise NotFoundError("Haydovchi topilmadi")
    return driver


async def update_driver(session: AsyncSession, driver_id: int, data: DriverUpdate) -> Driver:
    driver = await get_driver(session, driver_id)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(driver, field, value)
    await session.commit()
    return driver

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.utils import build_household_key, build_mahalla_key
from app.models import User
from app.schemas.user import UserRegister
from app.services.order_service import get_active_order

_PROFILE_FIELDS = (
    "full_name",
    "phone_number",
    "region",
    "district",
    "mahalla",
    "street",
    "house_number",
    "lpg_card_id",
)


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    return await session.scalar(select(User).where(User.telegram_id == telegram_id))


async def register_user(session: AsyncSession, data: UserRegister) -> User:
    """Ro'yxatdan o'tkazadi yoki mavjud profilni yangilaydi (upsert telegram_id bo'yicha)."""
    mahalla_key = build_mahalla_key(data.region, data.district, data.mahalla)
    household_key = build_household_key(
        data.region, data.district, data.mahalla, data.street, data.house_number
    )

    user = await get_user_by_telegram_id(session, data.telegram_id)
    if user is None:
        user = User(telegram_id=data.telegram_id)
        session.add(user)
    elif user.household_key != household_key and await get_active_order(session, user.id):
        raise InvalidStateError(
            "Sizda faol navbat bor. Manzilni o'zgartirish uchun avval navbatni bekor qiling."
        )

    for field in _PROFILE_FIELDS:
        setattr(user, field, getattr(data, field))
    user.mahalla_key = mahalla_key
    user.household_key = household_key

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise InvalidStateError("Bu Telegram akkaunt allaqachon ro'yxatdan o'tgan") from exc
    return user

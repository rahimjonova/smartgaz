from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.deps import ServiceAccess, SessionDep
from app.core.exceptions import NotFoundError
from app.schemas.user import UserOut, UserRegister
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Users — aholi"], dependencies=[ServiceAccess])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Ro'yxatdan o'tish / profilni yangilash (veb yoki boshqa mijozlar uchun)",
)
async def register(payload: UserRegister, session: SessionDep) -> UserOut:
    return UserOut.model_validate(await user_service.register_user(session, payload))


@router.get("/by-telegram/{telegram_id}", response_model=UserOut)
async def get_by_telegram(telegram_id: Annotated[int, Path(gt=0)], session: SessionDep) -> UserOut:
    user = await user_service.get_user_by_telegram_id(session, telegram_id)
    if user is None:
        raise NotFoundError("Foydalanuvchi topilmadi")
    return UserOut.model_validate(user)

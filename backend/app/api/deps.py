"""FastAPI dependency'lari: DB sessiya, API-kalit bo'yicha rollar, notifier."""

import secrets
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.services.notifier import Notifier

SessionDep = Annotated[AsyncSession, Depends(get_session)]

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="Rolga mos API kalit: admin, driver yoki service",
)


class Role(StrEnum):
    ADMIN = "admin"
    DRIVER = "driver"
    SERVICE = "service"  # bot / veb-mijoz


def _resolve_role(api_key: str) -> Role | None:
    candidates = (
        (Role.ADMIN, settings.ADMIN_API_KEY),
        (Role.DRIVER, settings.DRIVER_API_KEY),
        (Role.SERVICE, settings.SERVICE_API_KEY),
    )
    provided = api_key.encode()
    for role, expected in candidates:
        if secrets.compare_digest(provided, expected.encode()):
            return role
    return None


def require_roles(*allowed: Role) -> Callable[..., Awaitable[Role]]:
    """Admin har doim ruxsatga ega; qolganlar faqat `allowed` ro'yxatida bo'lsa."""

    async def dependency(api_key: Annotated[str | None, Security(api_key_header)]) -> Role:
        if not api_key:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "X-API-Key sarlavhasi talab qilinadi")
        role = _resolve_role(api_key)
        if role is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "API kalit noto'g'ri")
        if role is not Role.ADMIN and role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu amal uchun ruxsat yo'q")
        return role

    return dependency


AdminOnly = Depends(require_roles(Role.ADMIN))
DriverAccess = Depends(require_roles(Role.DRIVER))
ServiceAccess = Depends(require_roles(Role.SERVICE))
ServiceOrDriverAccess = Depends(require_roles(Role.SERVICE, Role.DRIVER))


def get_notifier(request: Request) -> Notifier:
    notifier: Notifier = request.app.state.notifier
    return notifier


NotifierDep = Annotated[Notifier, Depends(get_notifier)]

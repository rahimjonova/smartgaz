"""FastAPI ilovasi: `uvicorn app.main:app --reload`."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.deps import SessionDep
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import DomainError
from app.db.session import engine
from app.services.notifier import Notifier

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    bot: Bot | None = None
    if settings.BOT_TOKEN:
        bot = Bot(settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    app.state.notifier = Notifier(bot)
    try:
        yield
    finally:
        if bot is not None:
            await bot.session.close()
        await engine.dispose()


async def domain_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "code": exc.code},
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title=f"{settings.APP_NAME} API",
        version=settings.APP_VERSION,
        description=(
            "Qishloq hududlarida suyultirilgan gaz balonlari ta'minotini navbat, "
            "antifrod va GPS monitoring orqali tartibga soluvchi tizim."
        ),
        lifespan=lifespan,
    )
    app.add_exception_handler(DomainError, domain_error_handler)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/health", tags=["System"])
    async def health(session: SessionDep) -> dict[str, str]:
        await session.execute(text("SELECT 1"))
        return {"status": "ok"}

    return app


app = create_app()

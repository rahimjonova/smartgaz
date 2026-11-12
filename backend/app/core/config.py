"""Ilova konfiguratsiyasi (.env fayldan o'qiladi)."""

from decimal import Decimal
from functools import lru_cache
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # --- Umumiy ---
    APP_NAME: str = "SmartGaz"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    TIMEZONE: str = "Asia/Tashkent"

    # --- Ma'lumotlar bazasi ---
    # To'liq URL berilsa (masalan, Supabase), alohida POSTGRES_* maydonlari e'tiborga olinmaydi.
    DATABASE_URL: str | None = None
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "smartgaz"
    POSTGRES_PASSWORD: str = "smartgaz"
    POSTGRES_DB: str = "smartgaz"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = Field(default=10, ge=1)
    DB_MAX_OVERFLOW: int = Field(default=20, ge=0)

    # --- Telegram ---
    BOT_TOKEN: str = ""

    # --- API kalitlari (X-API-Key sarlavhasi) ---
    ADMIN_API_KEY: str = Field(min_length=16)
    DRIVER_API_KEY: str = Field(min_length=16)
    SERVICE_API_KEY: str = Field(min_length=16)

    # --- Biznes qoidalari ---
    REORDER_COOLDOWN_DAYS: int = Field(default=20, ge=1)
    DAILY_CAPACITY_PER_MAHALLA: int = Field(default=40, ge=1)
    CYLINDER_PRICE: Decimal = Field(default=Decimal("65000.00"), ge=0)
    DRIVER_ONLINE_THRESHOLD_SECONDS: int = Field(default=120, ge=30)
    GPS_UPDATE_INTERVAL_SECONDS: int = Field(default=30, ge=5)

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            for prefix in ("postgresql://", "postgres://"):
                if url.startswith(prefix):
                    return "postgresql+asyncpg://" + url[len(prefix) :]
            return url
        return (
            f"postgresql+asyncpg://{quote_plus(self.POSTGRES_USER)}:"
            f"{quote_plus(self.POSTGRES_PASSWORD)}@{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/{quote_plus(self.POSTGRES_DB)}"
        )

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.TIMEZONE)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()

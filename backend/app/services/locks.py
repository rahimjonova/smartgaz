from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def advisory_xact_lock(session: AsyncSession, key: str) -> None:
    """PostgreSQL tranzaksiya darajasidagi advisory lock.

    Bir mahalla uchun parallel so'rovlar (navbat raqami berish, antifrod tekshiruvi,
    marshrutga balon band qilish) ketma-ket bajarilishini kafolatlaydi.
    Lock commit/rollback paytida avtomatik bo'shaydi.
    """
    await session.execute(select(func.pg_advisory_xact_lock(func.hashtext(key))))

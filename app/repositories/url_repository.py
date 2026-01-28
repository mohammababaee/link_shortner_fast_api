from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from app.db.models import ShortURL


class URLRepository:
    @staticmethod
    async def get_by_short_code(session: AsyncSession, short_code: str) -> ShortURL | None:
        statement = select(ShortURL).where(ShortURL.short_code == short_code)
        result = await session.exec(statement)
        return result.first()

    @staticmethod
    async def create(session: AsyncSession, short_url: ShortURL) -> ShortURL:
        session.add(short_url)
        await session.commit()
        await session.refresh(short_url)
        return short_url
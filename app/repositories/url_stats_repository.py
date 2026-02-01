from sqlmodel import Session
from sqlmodel import select
from app.db.models import URLStats, ShortURL
from datetime import datetime
from sqlalchemy import update
from datetime import datetime, timezone


class URLStatsRepository:
    @staticmethod
    async def get_by_short_code(session: Session, short_code: str) -> URLStats | None:
        statement = select(URLStats).where(URLStats.short_code == short_code)
        result = await session.exec(statement)
        return result.first()

    @staticmethod
    async def create(session: Session, url_stats: URLStats) -> URLStats:
        session.add(url_stats)
        await session.commit()
        await session.refresh(url_stats)
        return url_stats

    @staticmethod
    async def increment_visit_count(session: Session, short_code: str):
        stmt = (
            update(URLStats)
            .where(URLStats.short_code == short_code)
            .values(
                visit_count=URLStats.visit_count + 1,
                last_visited_at=datetime.now()
            )
        )
        result = await session.exec(stmt)
        await session.commit()
        
        if result.rowcount == 0:
            new_stats = URLStats(short_code=short_code, visit_count=1, last_visited_at=datetime.now())
            session.add(new_stats)
            await session.commit()

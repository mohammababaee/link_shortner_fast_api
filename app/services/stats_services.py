from sqlmodel import Session
from app.repositories.url_stats_repository import URLStatsRepository
from app.db.models import URLStats
from datetime import datetime


class URLStatsService:
    def __init__(self, stats_repo: URLStatsRepository):
        self.stats_repo = stats_repo

    async def get_stats(self, session: Session, short_code: str) -> dict:
        """Get visit statistics for a short code"""
        stats = await self.stats_repo.get_by_short_code(session, short_code)

        if stats:
            return {
                "short_code": short_code,
                "visit_count": stats.visit_count,
                "last_visited_at": str(stats.last_visited_at)
            }

        return {
            "short_code": short_code,
            "visit_count": 0,
            "last_visited_at": None
        }

    async def increment_visit(self, session: Session, short_code: str):
        """Increment visit count for a short code"""
        await self.stats_repo.increment_visit_count(session, short_code)

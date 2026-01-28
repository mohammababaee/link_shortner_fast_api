from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.db.session import get_session
from app.repositories.url_stats_repository import URLStatsRepository
from app.services.url_service import URLService
from app.services.stats_services import URLStatsService
from app.repositories.url_repository import URLRepository
from app.api.schemas import ShortenRequest
from app.api.schemas import ShortenRequestResponse
from app.api.schemas import URLStats

router = APIRouter()


def get_url_service():
    return URLService(URLRepository())


def get_url_stats_service():
    return URLStatsService(URLStatsRepository())


@router.post("/shorten")
async def create_short_url(
        request: ShortenRequest,
        session: Session = Depends(get_session),
        service: URLService = Depends(get_url_service)
):
    short_url = await service.create_short_url(session, request.original_url)
    return ShortenRequestResponse(
        short_code=short_url.short_code,
        original_url=short_url.original_url
    )


@router.get("/{short_code}")
async def redirect_to_url(
        short_code: str,
        session: Session = Depends(get_session),
        service: URLService = Depends(get_url_service),
        stats_service: URLStatsService = Depends(get_url_stats_service)

):
    original_url = await service.get_original_url(session, short_code)
    if not original_url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    if not original_url.startswith(("http://", "https://")):
        original_url = f"https://{original_url}"

    await stats_service.increment_visit(session, short_code)

    return RedirectResponse(url=original_url, status_code=307)


@router.get("/stats/{short_code}")
async def get_url_stats(
        short_code: str,
        session: Session = Depends(get_session),
        stats_service: URLStatsService = Depends(get_url_stats_service)
):
    stats = await stats_service.get_stats(session, short_code)
    if stats["visit_count"] == 0:
        if not stats_service.get_stats(session, short_code):
            raise HTTPException(status_code=404, detail="Short URL not found")
    return URLStats(short_code=stats.get("short_code"), visit_count=stats.get("visit_count"),
                    last_visited_at=stats.get("last_visited_at"))

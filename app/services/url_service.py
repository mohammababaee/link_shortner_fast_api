from sqlmodel import Session
from app.repositories.url_repository import URLRepository
from app.db.models import ShortURL
from app.utils.short_code_generator import generate_short_code
from app.utils.url_validator import validate_url


class URLService:
    def __init__(self, repository: URLRepository):
        self.repository = repository

    async def create_short_url(self, session: Session, original_url: str) -> ShortURL:
        original_url = validate_url(original_url)

        MAX_ATTEMPTS = 5
        for _ in range(MAX_ATTEMPTS):
            short_code = generate_short_code()
            if not await self.repository.get_by_short_code(session, short_code):
                short_url = ShortURL(original_url=original_url, short_code=short_code)
                return await self.repository.create(session, short_url)

        raise HTTPException(status_code=500, detail="Failed to generate unique short code")

    async def get_original_url(self, session: Session, short_code: str) -> str | None:
        short_url = await self.repository.get_by_short_code(session, short_code)
        return short_url.original_url if short_url and short_url.is_active else None

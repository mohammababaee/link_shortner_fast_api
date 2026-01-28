from pydantic import BaseModel, HttpUrl


class ShortenRequest(BaseModel):
    original_url: str


class ShortenRequestResponse(BaseModel):
    short_code: str
    original_url: str


class URLStats(BaseModel):
    short_code: str
    visit_count: int
    last_visited_at: str | None

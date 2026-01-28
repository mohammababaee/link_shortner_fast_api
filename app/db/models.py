from sqlmodel import SQLModel, Field
from datetime import datetime

class BaseModel(SQLModel):
    __abstract__ = True
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"onupdate": datetime.utcnow},
        nullable=False
    )

class ShortURL(BaseModel, table=True):
    __tablename__ = "urls"
    __table_args__ = ({"extend_existing": True},)

    id: int | None = Field(default=None, primary_key=True)
    original_url: str
    short_code: str = Field(unique=True, index=True)
    is_active: bool = Field(default=True)


class URLStats(BaseModel, table=True):
    __tablename__ = "url_stats"

    id: int | None = Field(default=None, primary_key=True)
    short_code: str = Field(unique=True, index=True)
    visit_count: int = Field(default=0)
    last_visited_at: datetime | None = Field(default=None)
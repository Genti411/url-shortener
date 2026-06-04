"""Database layer (SQLAlchemy 2.0). PostgreSQL in Docker; SQLite for tests."""
import os
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, create_engine, func
from sqlalchemy.orm import (DeclarativeBase, Mapped, mapped_column, sessionmaker)

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./urls.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class ShortURL(Base):
    __tablename__ = "urls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    short_code: Mapped[str | None] = mapped_column(String(16), unique=True, index=True)
    original_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_accessed: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


def init_db() -> None:
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

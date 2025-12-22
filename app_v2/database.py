from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from utils.db_probe import resolve_db_url

Base = declarative_base()


def _build_engine(db_url: str | None = None):
    url = resolve_db_url(db_url)
    engine_kwargs: dict = {"pool_pre_ping": True}

    if url.startswith("postgresql://"):
        engine_kwargs["connect_args"] = {"connect_timeout": 3}
    if url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}

    return create_engine(url, **engine_kwargs)


@lru_cache(maxsize=1)
def get_engine(db_url: str | None = None):
    """Lazily create and cache the SQLAlchemy engine."""
    return _build_engine(db_url)


def get_session_maker(db_url: str | None = None):
    """Provide a sessionmaker bound to the lazily created engine."""
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine(db_url))


def get_db(db_url: str | None = None):
    """FastAPI dependency for database sessions"""
    SessionLocal = get_session_maker(db_url)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

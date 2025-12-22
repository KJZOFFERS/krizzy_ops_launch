import os
import time
from urllib.parse import urlparse, urlunparse

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


def resolve_db_url(raw_url: str | None = None) -> str:
    """
    Normalize and validate the database URL.

    - Accepts optional raw URL (falls back to DATABASE_URL env).
    - Normalizes postgres:// to postgresql:// for SQLAlchemy compatibility.
    - Rejects SQLite when running in non-local environments.
    """

    url = raw_url or os.environ.get("DATABASE_URL") or ""
    url = url.strip().strip('"').strip("'")

    if not url:
        raise ValueError("DATABASE_URL is not configured")

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    env = os.environ.get("ENVIRONMENT", "local").lower()
    if url.startswith("sqlite") and env not in {"local", "dev", "development", "test"}:
        raise ValueError("SQLite is not allowed outside local/test environments")

    return url


def redact_db_target(url: str) -> str:
    """Return a redacted version of the DB target with no secrets."""

    parsed = urlparse(url)
    host_hint = (parsed.hostname or "unknown").split(".")[0]
    db_name = parsed.path.lstrip("/") or "default"
    port = f":{parsed.port}" if parsed.port else ""
    redacted_netloc = f"{host_hint}{port}" if host_hint else "redacted"

    redacted = parsed._replace(netloc=redacted_netloc, path=f"/{db_name}", params="", query="", fragment="")
    return urlunparse(redacted)


def probe_db(raw_url: str | None = None, max_attempts: int = 2, timeout_seconds: int = 3) -> dict:
    """
    Attempt to connect to the database with bounded retries and strict timeout.

    Returns a structured result with only redacted output.
    """

    try:
        url = resolve_db_url(raw_url)
    except ValueError as exc:
        return {"ok": False, "error": str(exc), "target": None, "attempts": 0}

    target = redact_db_target(url)
    attempts = 0
    last_error: str | None = None

    connect_args = {"connect_timeout": timeout_seconds} if url.startswith("postgresql://") else {}

    while attempts < max_attempts:
        attempts += 1
        try:
            engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return {"ok": True, "target": target, "attempts": attempts}
        except SQLAlchemyError as exc:
            last_error = str(exc)
            time.sleep(1)

    return {"ok": False, "target": target, "attempts": attempts, "error": last_error}

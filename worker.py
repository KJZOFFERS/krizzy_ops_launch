"""Durable job worker that drains the jobs table."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app_v2.database import get_session_maker
from app_v2.models.job import Job
from engines.govcon_engine import run_govcon_engine
from engines.rei_engine import run_rei_engine
from utils.airtable_utils import update_record, write_record

logger = logging.getLogger("worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SessionLocal = get_session_maker()

MAX_ATTEMPTS = 5
BASE_BACKOFF_SECONDS = 30


def _backoff_seconds(attempt: int) -> int:
    # Exponential backoff with a sane upper bound (about 8 minutes at attempt 5)
    return min(30 * (2 ** max(0, attempt - 1)), 480)


def _fetch_next_job(session: Session) -> Optional[Job]:
    now = datetime.now(timezone.utc)
    stmt = (
        select(Job)
        .where(Job.status.in_(["pending", "retry"]), Job.run_at <= now)
        .order_by(Job.run_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    result = session.execute(stmt).scalars().first()
    return result


def _perform_sync_airtable(job: Job) -> None:
    payload = job.payload or {}
    method = payload.get("method")
    table = payload.get("table")
    fields = payload.get("fields")
    record_id = payload.get("record_id")

    if not method or not table or not isinstance(fields, dict):
        raise ValueError("sync_airtable missing required payload fields")

    if method == "write":
        write_record(table, fields)
    elif method == "update":
        if not record_id:
            raise ValueError("record_id required for update")
        update_record(table, record_id, fields)
    else:
        raise ValueError(f"Unsupported sync_airtable method: {method}")


def _perform_run_engine(job: Job) -> None:
    payload = job.payload or {}
    engine = payload.get("engine")
    if engine == "rei":
        run_rei_engine(payload=payload)
    elif engine == "govcon":
        run_govcon_engine(payload=payload)
    else:
        raise ValueError(f"Unknown engine: {engine}")


HANDLERS: Dict[str, Callable[[Job], None]] = {
    "sync_airtable": _perform_sync_airtable,
    "run_engine": _perform_run_engine,
}


def _process_job(session: Session, job: Job) -> None:
    job.status = "processing"
    job.attempts += 1
    session.commit()

    handler = HANDLERS.get(job.type)
    if not handler:
        raise ValueError(f"No handler for job type {job.type}")

    handler(job)


def _handle_failure(session: Session, job: Job, error: Exception) -> None:
    job.last_error = f"{type(error).__name__}: {error}"

    if job.attempts >= MAX_ATTEMPTS:
        job.status = "failed"
        logger.error("Job %s failed permanently: %s", job.id, job.last_error)
    else:
        job.status = "retry"
        next_run = datetime.now(timezone.utc) + timedelta(seconds=_backoff_seconds(job.attempts))
        job.run_at = next_run
        logger.warning(
            "Job %s failed (attempt %s). Retrying at %s. Error: %s",
            job.id,
            job.attempts,
            next_run.isoformat(),
            job.last_error,
        )

    session.commit()


def _handle_success(session: Session, job: Job) -> None:
    job.status = "completed"
    job.last_error = None
    session.commit()


def _worker_loop() -> None:
    while True:
        session: Session = SessionLocal()
        try:
            job = _fetch_next_job(session)
            if not job:
                session.close()
                time.sleep(2)
                continue

            try:
                _process_job(session, job)
            except Exception as exc:  # noqa: BLE001
                _handle_failure(session, job, exc)
            else:
                _handle_success(session, job)
        except SQLAlchemyError as exc:
            logger.error("Worker DB error: %s", exc)
            time.sleep(5)
        finally:
            session.close()


if __name__ == "__main__":
    logger.info("Starting job worker...")
    _worker_loop()

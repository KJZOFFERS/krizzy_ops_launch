"""Lightweight job enqueue helpers for the durable queue."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app_v2.database import get_session_maker
from app_v2.models.job import Job

SessionLocal = get_session_maker()


def enqueue_job(
    job_type: str,
    payload: Optional[Dict[str, Any]] = None,
    run_at: Optional[datetime] = None,
    db: Optional[Session] = None,
) -> Job:
    """Persist a job to the durable queue.

    If no session is provided, a new one is created and closed automatically.
    """

    own_session = db is None
    session = db or SessionLocal()
    try:
        job = Job(
            type=job_type,
            payload=payload or {},
            run_at=run_at or datetime.now(timezone.utc),
            status="pending",
        )

        session.add(job)
        session.commit()
        session.refresh(job)
        return job
    finally:
        if own_session:
            session.close()


def enqueue_sync_airtable(
    table: str,
    fields: Dict[str, Any],
    *,
    method: str,
    record_id: Optional[str] = None,
    run_at: Optional[datetime] = None,
    db: Optional[Session] = None,
) -> Job:
    """Schedule an Airtable sync job (write/update).

    This avoids blocking ingestion/scoring paths on network calls.
    """

    payload: Dict[str, Any] = {
        "method": method,
        "table": table,
        "fields": fields,
    }

    if record_id:
        payload["record_id"] = record_id

    return enqueue_job("sync_airtable", payload=payload, run_at=run_at, db=db)


def enqueue_engine_run(engine: str, payload: Optional[Dict[str, Any]] = None, db: Optional[Session] = None) -> Job:
    """Helper for queuing engine execution jobs."""

    job_payload = {"engine": engine}
    if payload:
        job_payload.update(payload)

    return enqueue_job("run_engine", payload=job_payload, db=db)


def enqueue_match_buyers(
    deal_id: int,
    details: Optional[Dict[str, Any]] = None,
    db: Optional[Session] = None,
) -> Job:
    """Queue a buyer-matching event for downstream processors."""

    payload: Dict[str, Any] = {"deal_id": deal_id}
    if details:
        payload.update(details)

    return enqueue_job("match_buyers", payload=payload, db=db)

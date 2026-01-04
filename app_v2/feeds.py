from __future__ import annotations

import datetime
import math
import uuid
from typing import Any, Dict, List, Optional, Tuple

import requests
from sqlalchemy import text
from sqlalchemy.orm import Session

from app_v2 import config
from app_v2.models.ops import OpsKV, OpsLedger, advisory_lock_key
from app_v2.utils.airtable_safe import upsert_records
from app_v2.utils.logger import get_logger

logger = get_logger(__name__)

SAM_ENDPOINT = "https://api.sam.gov/opportunities/v2/search"

# Airtable constants
GOVCON_TABLE_ID = "tblD9uurYJe33RvrM"
GOVCON_MERGE_FIELD_ID = "fldfVSs5LrqHkS2cK"  # External_Id
GOVCON_FALLBACK_FIELD_ID = "fldwgt9wLP2ViVjxl"  # Solicitation Number

LEADS_REI_TABLE_ID = "tbl1k98DeudVoMkoL"
LEADS_REI_MERGE_FIELD_ID = "fldU5SYnljXAnowVm"
LEADS_REI_FALLBACK_FIELD_ID = "fldNcNTATOdOk8GOf"


class FeedError(Exception):
    ...


def _format_mmddyyyy(date: datetime.date) -> str:
    return date.strftime("%m/%d/%Y")


def _parse_posted_date(raw: str) -> Optional[datetime.datetime]:
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _get_kv(session: Session, key: str) -> Optional[Dict[str, Any]]:
    kv = session.get(OpsKV, key)
    return kv.value_json if kv else None


def _set_kv(session: Session, key: str, value: Dict[str, Any]) -> None:
    kv = session.get(OpsKV, key)
    if kv:
        kv.value_json = value
    else:
        kv = OpsKV(key=key, value_json=value)
        session.add(kv)
    session.commit()


def _log_ledger(
    session: Session,
    *,
    run_id: str,
    feed: str,
    status: str,
    message: str,
    records_processed: int,
    cursor_value: Optional[str],
    error: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    entry = OpsLedger(
        run_id=run_id,
        feed=feed,
        status=status,
        message=message,
        error=error,
        records_processed=records_processed,
        cursor_value=cursor_value,
        meta=meta,
    )
    session.add(entry)
    session.commit()


def _acquire_advisory_lock(session: Session, feed_name: str) -> bool:
    key = advisory_lock_key(feed_name)
    try:
        locked = session.execute(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": key}).scalar()
        return bool(locked)
    except Exception:
        # If DB does not support advisory locks (e.g., SQLite), continue without locking
        logger.warning("Advisory lock not supported; proceeding without lock", exc_info=True)
        return True


def _sam_query_params(
    *,
    posted_from: str,
    posted_to: str,
    rdl_from: str,
    rdl_to: str,
    offset: int,
    limit: int,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "postedFrom": posted_from,
        "postedTo": posted_to,
        "rdlfrom": rdl_from,
        "rdlto": rdl_to,
        "limit": min(limit, 1000),
        "offset": offset,
        "api_key": config.SAM_API_KEY,
    }
    if config.GOVCON_PTYPE:
        params["ptype"] = config.GOVCON_PTYPE
    naics_codes = config.get_naics_codes()
    if naics_codes:
        params["ncode"] = ",".join(naics_codes)
    if config.GOVCON_SETASIDE:
        params["typeOfSetAside"] = config.GOVCON_SETASIDE
    return params


def _fetch_sam_page(params: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.get(SAM_ENDPOINT, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def _normalize_govcon_record(raw: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[datetime.datetime]]:
    notice_id = raw.get("noticeId") or raw.get("id")
    solicitation = raw.get("solicitationNumber") or notice_id
    title = raw.get("title") or raw.get("description")
    posted_date = raw.get("postedDate") or raw.get("posted")
    posted_dt = _parse_posted_date(posted_date) if posted_date else None
    deadline = raw.get("responseDeadLine") or raw.get("responseDeadlines")
    url = raw.get("uiLink") or raw.get("url") or raw.get("link")
    naics = raw.get("naicsCode") or raw.get("ncode")
    set_aside = raw.get("typeOfSetAside")
    fields = {
        "External_Id": notice_id,
        "Solicitation Number": solicitation,
        "Title": title,
        "Posted Date": posted_date,
        "Response Deadline": deadline,
        "Source_URL": url,
        "NAICS": naics,
        "Set Aside": set_aside,
        "Notice Type": raw.get("type"),
    }
    return fields, posted_dt


def run_govcon_feed(session: Session) -> Dict[str, Any]:
    feed_name = "govcon"
    run_id = str(uuid.uuid4())
    if not _acquire_advisory_lock(session, feed_name):
        raise FeedError("Failed to acquire advisory lock")

    last_kv = _get_kv(session, f"{feed_name}:last_success")
    last_watermark = None
    if last_kv and "timestamp" in last_kv:
        try:
            last_watermark = datetime.datetime.fromisoformat(last_kv["timestamp"])
        except ValueError:
            last_watermark = None

    today = datetime.datetime.utcnow().date()
    start_date = (last_watermark.date() if last_watermark else today)
    posted_from = _format_mmddyyyy(start_date)
    posted_to = _format_mmddyyyy(today)
    rdl_from = config.GOVCON_RDL_FROM or posted_from
    rdl_to = config.GOVCON_RDL_TO or posted_to

    limit = 1000
    offset = 0
    processed = 0
    latest_seen: Optional[datetime.datetime] = last_watermark
    collected_records: List[Dict[str, Any]] = []

    try:
        while True:
            params = _sam_query_params(
                posted_from=posted_from,
                posted_to=posted_to,
                rdl_from=rdl_from,
                rdl_to=rdl_to,
                offset=offset,
                limit=limit,
            )
            payload = _fetch_sam_page(params)
            items = payload.get("opportunitiesData", [])
            if not items:
                break

            filtered: List[Dict[str, Any]] = []
            for item in items:
                record, posted_dt = _normalize_govcon_record(item)
                if last_watermark and posted_dt and posted_dt <= last_watermark:
                    # client-side filter to prevent skipping items due to date-only window
                    continue
                filtered.append(record)
                if posted_dt and (latest_seen is None or posted_dt > latest_seen):
                    latest_seen = posted_dt

            if filtered:
                saved = upsert_records(
                    base_id=config.AIRTABLE_BASE_ID,
                    table_id=GOVCON_TABLE_ID,
                    token=config.AIRTABLE_PAT,
                    records=filtered,
                    merge_field_id=GOVCON_MERGE_FIELD_ID,
                    fallback_field_id=GOVCON_FALLBACK_FIELD_ID,
                )
                processed += len(saved)
            offset += 1
            if len(items) < limit:
                break
    except Exception as exc:  # noqa: BLE001
        _log_ledger(
            session,
            run_id=run_id,
            feed=feed_name,
            status="error",
            message="GovCon feed failed",
            error=str(exc),
            records_processed=processed,
            cursor_value=latest_seen.isoformat() if latest_seen else None,
            meta={"posted_from": posted_from, "posted_to": posted_to, "rdl_from": rdl_from, "rdl_to": rdl_to},
        )
        raise

    if latest_seen:
        _set_kv(session, f"{feed_name}:last_success", {"timestamp": latest_seen.isoformat()})
    _log_ledger(
        session,
        run_id=run_id,
        feed=feed_name,
        status="success",
        message="GovCon feed run complete",
        records_processed=processed,
        cursor_value=latest_seen.isoformat() if latest_seen else None,
        meta={"posted_from": posted_from, "posted_to": posted_to, "rdl_from": rdl_from, "rdl_to": rdl_to},
    )
    return {
        "run_id": run_id,
        "processed": processed,
        "cursor": latest_seen.isoformat() if latest_seen else None,
        "window": {"posted_from": posted_from, "posted_to": posted_to, "rdl_from": rdl_from, "rdl_to": rdl_to},
    }


def run_rei_feed(session: Session) -> Dict[str, Any]:
    """
    Placeholder REI feed to normalize source URLs and upsert idempotently to Leads_REI table.
    """
    feed_name = "rei"
    run_id = str(uuid.uuid4())
    if not _acquire_advisory_lock(session, feed_name):
        raise FeedError("Failed to acquire advisory lock")

    sources = config.get_rei_sources()
    processed = 0
    normalized_records: List[Dict[str, Any]] = []
    for source in sources:
        url = source.get("url")
        external_id = source.get("external_id") or url
        if not url or not external_id:
            continue
        # normalize url (strip fragments/query for idempotence)
        normalized_url = url.split("#")[0]
        normalized_records.append(
            {
                "External_Id": external_id,
                "Source_URL": normalized_url,
                "Raw_Source": source,
            }
        )

    try:
        if normalized_records:
            saved = upsert_records(
                base_id=config.AIRTABLE_BASE_ID,
                table_id=LEADS_REI_TABLE_ID,
                token=config.AIRTABLE_PAT,
                records=normalized_records,
                merge_field_id=LEADS_REI_MERGE_FIELD_ID,
                fallback_field_id=LEADS_REI_FALLBACK_FIELD_ID,
            )
            processed = len(saved)
    except Exception as exc:  # noqa: BLE001
        _log_ledger(
            session,
            run_id=run_id,
            feed=feed_name,
            status="error",
            message="REI feed failed",
            error=str(exc),
            records_processed=processed,
            cursor_value=None,
            meta={"sources": len(sources)},
        )
        raise

    _log_ledger(
        session,
        run_id=run_id,
        feed=feed_name,
        status="success",
        message="REI feed run complete",
        records_processed=processed,
        cursor_value=None,
        meta={"sources": len(sources)},
    )
    return {"run_id": run_id, "processed": processed}


def get_feed_status(session: Session) -> Dict[str, Any]:
    status = {
        "govcon": _get_kv(session, "govcon:last_success"),
        "rei": _get_kv(session, "rei:last_success"),
    }
    recent = (
        session.query(OpsLedger)
        .order_by(OpsLedger.created_at.desc())
        .limit(10)
        .all()
    )
    status["recent_runs"] = [
        {
            "run_id": r.run_id,
            "feed": r.feed,
            "status": r.status,
            "records_processed": r.records_processed,
            "cursor_value": r.cursor_value,
            "message": r.message,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in recent
    ]
    return status

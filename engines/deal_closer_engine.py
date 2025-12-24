import json
import logging
import threading
import time
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app_v2.database import get_session_maker
from app_v2.models.deal import Deal
from app_v2.models.pending_deal import PendingDeal
from app_v2.utils.gmail_client import (
    GmailClient,
    extract_address,
    extract_deadline,
    extract_price,
    extract_sender_name,
)
from job_queue import enqueue_match_buyers
from utils.discord_utils import post_error, post_ops

logger = logging.getLogger("deal_closer_engine")

SessionLocal = get_session_maker()

KEYWORDS = ["contract", "assignment", "offer", "counter"]
deal_closer_lock = threading.Lock()


def _parse_thread_into_deal(thread: Dict[str, Any]) -> Optional[Deal]:
    """Convert parsed Gmail thread into Deal model."""
    text = thread.get("text", "") or ""
    address = extract_address(text) or ""
    if not address:
        return None

    asking = extract_price(text)
    seller_name = extract_sender_name(thread.get("from", ""))
    deadline = extract_deadline(text)

    deal = Deal(
        external_id=thread.get("id", ""),
        source="GMAIL",
        address=address,
        city="",
        state="",
        zip_code="",
        asking=asking,
        seller_name=seller_name,
        deadline=deadline,
        raw_payload=json.dumps(
            {
                "thread_id": thread.get("id"),
                "subject": thread.get("subject"),
                "from": thread.get("from"),
                "timestamp": thread.get("timestamp").isoformat() if thread.get("timestamp") else None,
                "preview": text[:2000],
            }
        ),
        status="PENDING",
    )
    return deal


def _persist_pending_deal(session: Session, deal: Deal, thread_summary: Dict[str, Any]) -> Optional[PendingDeal]:
    """Write new deals into deals_pending if not already present."""
    existing = session.query(PendingDeal).filter_by(thread_id=deal.external_id).first()
    if existing:
        return None

    pending = PendingDeal(
        thread_id=deal.external_id,
        property_address=deal.address,
        asking_price=deal.asking,
        seller_name=deal.seller_name,
        deadline=deal.deadline,
        raw_thread=thread_summary,
    )

    session.add(pending)
    session.commit()
    session.refresh(pending)
    return pending


def run_deal_closer_engine(payload: Dict[str, Any] | None = None) -> None:
    """
    Deal Closer engine:
    - Pulls Gmail threads with negotiation keywords.
    - Extracts address, asking, seller name, deadline.
    - Stores to deals_pending table.
    - Emits match_buyers events.
    """
    run_forever = bool(payload.get("loop_forever")) if isinstance(payload, dict) else False
    sleep_seconds = int(payload.get("sleep_seconds", 300)) if isinstance(payload, dict) else 300
    max_threads = int(payload.get("max_threads", 15)) if isinstance(payload, dict) else 15
    lookback_days = int(payload.get("lookback_days", 7)) if isinstance(payload, dict) else 7

    while True:
        if not deal_closer_lock.acquire(blocking=False):
            if not run_forever:
                return
            time.sleep(sleep_seconds)
            continue

        session: Session = SessionLocal()
        ingested = 0
        try:
            gmail_client = GmailClient()
            threads = gmail_client.fetch_threads(KEYWORDS, max_threads=max_threads, newer_than_days=lookback_days)
            for raw_thread in threads:
                parsed = GmailClient.parse_thread(raw_thread)
                deal = _parse_thread_into_deal(parsed)
                if not deal:
                    continue

                summary = {
                    "id": parsed.get("id"),
                    "subject": parsed.get("subject"),
                    "from": parsed.get("from"),
                    "timestamp": parsed.get("timestamp").isoformat() if parsed.get("timestamp") else None,
                    "preview": (parsed.get("text") or "")[:2000],
                }

                try:
                    pending = _persist_pending_deal(session, deal, summary)
                except Exception as exc:  # noqa: BLE001
                    session.rollback()
                    logger.error("Failed to persist pending deal %s: %s", deal.external_id, exc)
                    post_error(f"🔴 Deal closer persist error for {deal.external_id}: {exc}")
                    continue

                if not pending:
                    continue

                enqueue_match_buyers(
                    pending.id,
                    {
                        "address": pending.property_address,
                        "asking_price": pending.asking_price,
                        "seller_name": pending.seller_name,
                        "deadline": pending.deadline.isoformat() if pending.deadline else None,
                    },
                    db=session,
                )

                ingested += 1

            if ingested:
                post_ops(f"🟢 Deal closer ingested {ingested} new deal(s)")

        except Exception as exc:  # noqa: BLE001
            logger.error("Deal closer engine error: %s", exc, exc_info=True)
            post_error(f"🔴 Deal closer engine error: {type(exc).__name__}: {exc}")

        finally:
            session.close()
            if deal_closer_lock.locked():
                deal_closer_lock.release()
            if not run_forever:
                return
            time.sleep(sleep_seconds)

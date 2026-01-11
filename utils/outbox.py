import hashlib
from typing import List, Dict
from sqlalchemy import select, update
from utils.models import SmsOutbox


def _idempotency_id(lead_id: str, buyer_id: str, campaign_id: str) -> str:
    raw = f"{lead_id}|{buyer_id}|{campaign_id}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


def enqueue_messages(session, run_id: str, campaign_id: str, items: List[Dict]) -> int:
    """
    items: [{lead_id, buyer_id, to, body}]
    """
    n = 0
    for it in items:
        msg_id = _idempotency_id(it["lead_id"], it["buyer_id"], campaign_id)
        # Upsert-like: if exists, skip
        exists = session.get(SmsOutbox, msg_id)
        if exists:
            continue
        row = SmsOutbox(
            id=msg_id,
            run_id=run_id,
            lead_id=it["lead_id"],
            buyer_id=it["buyer_id"],
            to=it["to"],
            body=it["body"],
            status="QUEUED",
        )
        session.add(row)
        n += 1
    session.commit()
    return n


def dequeue_batch(session, limit: int = 50) -> List[SmsOutbox]:
    # Postgres SKIP LOCKED would be best, but keep it simple unless you confirm Postgres usage.
    rows = session.execute(
        select(SmsOutbox).where(SmsOutbox.status == "QUEUED").limit(limit)
    ).scalars().all()
    return rows


def mark_sent(session, msg_id: str, provider_msg_id: str):
    session.execute(
        update(SmsOutbox).where(SmsOutbox.id == msg_id).values(status="SENT", provider_msg_id=provider_msg_id)
    )
    session.commit()


def mark_failed(session, msg_id: str, error: str):
    session.execute(
        update(SmsOutbox).where(SmsOutbox.id == msg_id).values(status="FAILED", error=error[:2000])
    )
    session.commit()

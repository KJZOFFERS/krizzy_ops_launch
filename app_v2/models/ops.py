from datetime import datetime
import hashlib
from sqlalchemy import Column, DateTime, Integer, String, JSON, Text, Boolean, Index
from sqlalchemy.sql import func

from app_v2.database import Base


def advisory_lock_key(name: str) -> int:
    """
    Derive a stable bigint advisory lock key from feed name.
    Uses the first 8 bytes of sha256 digest.
    """
    digest = hashlib.sha256(name.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


class OpsKV(Base):
    __tablename__ = "ops_kv"

    key = Column(String(128), primary_key=True, index=True)
    value_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class OpsLedger(Base):
    __tablename__ = "ops_ledger"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(64), nullable=False, index=True)
    feed = Column(String(64), nullable=False, index=True)
    status = Column(String(16), nullable=False)  # success | error
    message = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    records_processed = Column(Integer, default=0)
    cursor_value = Column(String(64), nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


Index("idx_ops_ledger_feed_created", OpsLedger.feed, OpsLedger.created_at.desc())

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Float,
    Boolean,
    Index
)
from sqlalchemy.sql import func
from database import Base


class Ledger(Base):
    __tablename__ = "ledger"

    id = Column(Integer, primary_key=True, index=True)

    # Which engine produced the action
    engine = Column(String(32), nullable=False, index=True)

    # What happened (tick, ingest, outbound, bid, etc.)
    action = Column(String(64), nullable=False)

    # Optional external reference
    reference_id = Column(String(128), nullable=True)

    # Financial truth
    value_estimate = Column(Float, default=0.0)
    cash_realized = Column(Float, default=0.0)
    cost = Column(Float, default=0.0)

    # Outcome flag
    success = Column(Boolean, default=True)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())


Index("idx_ledger_engine_action", Ledger.engine, Ledger.action)

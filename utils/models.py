from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean, func, Index

Base = declarative_base()


class OpsKV(Base):
    __tablename__ = "ops_kv"
    k = Column(String(120), primary_key=True)
    v = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class OpsLedger(Base):
    __tablename__ = "ops_ledger"
    id = Column(String(64), primary_key=True)  # run_id:action_id etc
    run_id = Column(String(64), nullable=False, index=True)
    action = Column(String(120), nullable=False)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SmsOutbox(Base):
    __tablename__ = "sms_outbox"
    id = Column(String(64), primary_key=True)  # deterministic idempotency key
    run_id = Column(String(64), nullable=False, index=True)
    lead_id = Column(String(64), nullable=True)
    buyer_id = Column(String(64), nullable=True)
    to = Column(String(32), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, index=True)  # QUEUED|SENT|FAILED
    provider_msg_id = Column(String(80), nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


Index("ix_sms_outbox_status_created", SmsOutbox.status, SmsOutbox.created_at)

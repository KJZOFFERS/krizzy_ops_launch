from sqlalchemy import Column, DateTime, Float, Integer, String, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app_v2.database import Base


class PendingDeal(Base):
    __tablename__ = "deals_pending"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(128), nullable=False, unique=True, index=True)
    property_address = Column(String(512), nullable=False)
    asking_price = Column(Float, nullable=True)
    seller_name = Column(String(256), nullable=True)
    deadline = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), nullable=False, default="pending", index=True)
    raw_thread = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


Index("idx_deals_pending_status", PendingDeal.status)

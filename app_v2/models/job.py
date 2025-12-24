from sqlalchemy import Column, DateTime, Integer, String, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app_v2.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(64), nullable=False, index=True)
    status = Column(String(16), nullable=False, default="pending", index=True)
    run_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    payload = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


Index("idx_jobs_status_run_at", Job.status, Job.run_at)
Index("idx_jobs_type_status", Job.type, Job.status)

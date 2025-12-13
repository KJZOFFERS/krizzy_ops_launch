from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from sqlalchemy.sql import func
from app_v2.database import Base

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    engine = Column(String(32), nullable=False, index=True)   # rei | govcon
    action = Column(String(64), nullable=False)               # process_cycle
    status = Column(String(16), default="pending", index=True)
    attempts = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

Index("idx_jobs_engine_status", Job.engine, Job.status)

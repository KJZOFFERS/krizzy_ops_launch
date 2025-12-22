# Compatibility shim - imports from canonical source
from app_v2.database import Base, get_db, get_engine, get_session_maker

__all__ = ["Base", "get_db", "get_engine", "get_session_maker"]

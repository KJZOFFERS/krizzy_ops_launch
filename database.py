# Compatibility shim - imports from canonical source
from app_v2.database import engine, SessionLocal, Base, get_db

__all__ = ["engine", "SessionLocal", "Base", "get_db"]

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

_engine = None
_Session = None


def get_engine(database_url: str):
    global _engine, _Session
    if _engine is None:
        _engine = create_engine(database_url, pool_pre_ping=True, future=True)
        _Session = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
    return _engine


def get_session(database_url: str):
    get_engine(database_url)
    return _Session()


def db_ping(database_url: str) -> dict:
    try:
        eng = get_engine(database_url)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)[:2000]}

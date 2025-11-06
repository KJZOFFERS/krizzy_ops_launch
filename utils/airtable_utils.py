from __future__ import annotations
from typing import Any, Dict, Optional
from loguru import logger
try:
    from pyairtable import Table
except Exception:
    Table = None  # offline
def _table(api_key: str, base_id: str, table_name: str):
    if Table is None:
        raise RuntimeError("pyairtable not available offline")
    return Table(api_key, base_id, table_name)
def fetch_table(api_key: str, base_id: str, table_name: str, view: Optional[str] = None, formula: Optional[str] = None) -> list[dict]:
    try:
        t = _table(api_key, base_id, table_name)
        return t.all(view=view, formula=formula)
    except Exception as e:
        logger.debug(f"Airtable fetch skipped/offline: {e}")
        return []
def create_record(api_key: str, base_id: str, table_name: str, fields: Dict[str, Any]) -> Optional[dict]:
    try:
        t = _table(api_key, base_id, table_name)
        return t.create(fields)
    except Exception as e:
        logger.debug(f"Airtable write skipped/offline: {e}")
        return None
def safe_airtable_write(api_key: Optional[str], base_id: Optional[str], table_name: str, fields: Dict[str, Any]) -> bool:
    if not api_key or not base_id or Table is None:
        logger.debug("Airtable not configured or offline. Skipping write.")
        return False
    return create_record(api_key, base_id, table_name, fields) is not None

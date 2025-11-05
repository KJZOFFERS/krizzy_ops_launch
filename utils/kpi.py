from __future__ import annotations
import os
from datetime import datetime, timezone
from typing import Dict, Any
from .airtable_utils import create_record

def _kpi_table() -> str:
    return os.getenv("AT_TABLE_KPI") or os.getenv("AIRTABLE_TABLE_KPI") or "KPI_Log"

def log_kpi(event: str, fields: Dict[str, Any] | None = None) -> Dict[str, Any] | None:
    """
    Write a KPI record to Airtable if envs exist. No-op if not configured.
    Returns Airtable response dict, or None if skipped.
    """
    base = os.getenv("AIRTABLE_BASE_ID")
    key  = os.getenv("AIRTABLE_API_KEY")
    if not base or not key:
        return None

    data = {
        "Event": event,
        "Service": os.getenv("SERVICE_NAME", "krizzy_ops_web"),
        "Env": os.getenv("ENV", "production"),
        "TS": datetime.now(timezone.utc).isoformat(),
    }
    if fields:
        data.update(fields)
    return create_record(_kpi_table(), data)

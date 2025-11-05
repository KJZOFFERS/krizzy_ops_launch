from __future__ import annotations
import os
import time
from typing import Any, Dict

# Lazy import inside function to avoid import-time failures if envs are missing
def _table_name() -> str:
    return (
        os.getenv("AIRTABLE_TABLE_KPI_LOG")
        or os.getenv("AT_TABLE_KPI")
        or "KPI_Log"
    )

def log_kpi(event: str, payload: Dict[str, Any] | None = None) -> None:
    fields: Dict[str, Any] = {"event": event, "ts": int(time.time())}
    if payload:
        for k, v in payload.items():
            if isinstance(v, (str, int, float, bool)) or v is None:
                fields[k] = v
            else:
                fields[k] = str(v)
    try:
        from .airtable_utils import create_record
        create_record(_table_name(), fields)
    except Exception:
        # Never block app on KPI logging
        pass

def compute_kpi(data):
    return sum(data) / len(data) if data else 0

import os
import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from pyairtable import Table
from pyairtable.api import Api


AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
KPI_TABLE_NAME = "KPI_Log"
SERVICE_NAME = os.getenv("SERVICE_NAME", "krizzy_ops_web")


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _table_or_none() -> Optional[Table]:
    if not (AIRTABLE_API_KEY and AIRTABLE_BASE_ID):
        return None
    api = Api(AIRTABLE_API_KEY)
    return api.table(AIRTABLE_BASE_ID, KPI_TABLE_NAME)


async def kpi_log_safe(event: str, meta: Optional[Dict[str, Any]] = None) -> bool:
    """
    Safe, idempotent-ish KPI log write.
    - No-ops if Airtable envs are missing.
    - Stores meta as JSON string to avoid schema issues.
    """
    tbl = _table_or_none()
    if not tbl:
        return False

    fields = {
        "Event": event,
        "Service": SERVICE_NAME,
        "Timestamp": _now_iso(),
        "Meta": json.dumps(meta or {}, ensure_ascii=False),
    }

    try:
        tbl.create(fields)
        return True
    except Exception:
        # swallow errors to avoid bringing the service down
        return False

"""KPI tracking module for KRIZZY OPS."""

import os
import datetime
from typing import Any, Dict
from pyairtable import Table


AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")


def kpi_push(event: str, data: Dict[str, Any]) -> None:
    """
    Push KPI event to Airtable.

    Args:
        event: Event name (e.g., "boot", "cycle_start", "cycle_end", "error")
        data: Event data dictionary
    """
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        return

    try:
        table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, "KPI_Log")
        record = {
            "Event": event,
            "Data": str(data),
            "Timestamp": datetime.datetime.utcnow().isoformat(),
        }
        table.create(record)
    except Exception:
        pass

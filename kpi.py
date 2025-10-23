from __future__ import annotations

import datetime
import json
from typing import Any, Dict

from airtable_utils import safe_airtable_write


def kpi_push(event: str, data: Dict[str, Any]) -> None:
    """Write KPI event to Airtable in an idempotent way.

    Uses a deterministic dedupe key of event + iso date to avoid duplicates
    during retries while still recording multiple events per day.
    """
    ts = datetime.datetime.utcnow().isoformat()
    record = {
        "Event": event,
        "Data": json.dumps(data, separators=(",", ":")),
        "Timestamp": ts,
        # Dedupe fields
        "event_key": f"{event}:{ts[:10]}",
    }
    safe_airtable_write("KPI_Log", record, key_fields=["event_key", "Event"])

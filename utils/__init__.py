from __future__ import annotations

__all__ = [
    "list_records",
    "create_record",
    "update_record",
    "upsert_record",
    "fetch_table",
    "safe_airtable_write",
    "log_kpi",
]

from .airtable_utils import (
    list_records,
    create_record,
    update_record,
    upsert_record,
    fetch_table,
    safe_airtable_write,
)

try:
    from .kpi import log_kpi  # exported for callers that used utils.log_kpi
except Exception:  # safe fallback if KPI not configured
    def log_kpi(*_args, **_kwargs):
        return None

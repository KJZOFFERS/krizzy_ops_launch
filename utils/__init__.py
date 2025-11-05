__all__ = [
    "list_records",
    "create_record",
    "update_record",
    "upsert_record",
    "log_kpi",
    "heartbeat",
]

def __getattr__(name: str):
    if name in ("list_records", "create_record", "update_record", "upsert_record"):
        from .airtable_utils import (
            list_records,
            create_record,
            update_record,
            upsert_record,
        )
        return {
            "list_records": list_records,
            "create_record": create_record,
            "update_record": update_record,
            "upsert_record": upsert_record,
        }[name]
    if name == "log_kpi":
        from .kpi import log_kpi
        return log_kpi
    if name == "heartbeat":
        from .watchdog import heartbeat
        return heartbeat
    raise AttributeError(name)

try:
    from .kpi import log_kpi  # exported for callers that used utils.log_kpi
except Exception:  # safe fallback if KPI not configured
    def log_kpi(*_args, **_kwargs):
        return None

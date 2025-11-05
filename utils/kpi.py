# FILE: kpi.py
from __future__ import annotations
import time, os
from utils import upsert_record, create_record

KPI_TABLE = os.getenv("AIRTABLE_TABLE_KPI_LOG", "KPI_Log")

def kpi_log(service: str, status: str, **metrics):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    fields = {"timestamp": ts, "service": service, "status": status, **metrics}
    # create simple append record; if you want dedupe, use upsert on a composite key
    try:
        return create_record(KPI_TABLE, fields)
    except Exception:
        # last resort: ignore KPI failure
        return {}

from airtable_utils import safe_write
import time

def kpi_push(event, data):
    data["event"] = event
    data["ts"] = int(time.time())
    safe_write("KPI_Log", data)

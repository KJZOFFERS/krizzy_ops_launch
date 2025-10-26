from utils.airtable_utils import push_record
import time

def kpi_push(event, data):
    payload = {"Event": event, "Timestamp": int(time.time()), **data}
    push_record("KPI_Log", payload)

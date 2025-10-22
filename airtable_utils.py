import os
from pyairtable import Table

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

def push_record(table_name: str, data: dict):
    table = Table(AIRTABLE_API_KEY, AIRTABLE_BASE_ID, table_name)
    return table.create(data)

def log_kpi(event: str, data: dict):
    push_record("KPI_Log", {"Event": event, "Data": str(data)})

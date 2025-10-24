from pyairtable import Table
import os, time, json

def push(event, data):
    api = os.getenv("AIRTABLE_API_KEY")
    base = os.getenv("AIRTABLE_BASE_ID")
    table = os.getenv("TABLE_KPI_LOG", "KPI_Log")
    Table(api, base, table).create({
        "event": event,
        "data": json.dumps(data),
        "timestamp": int(time.time())
    })


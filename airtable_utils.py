import os, requests, datetime
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
HEADERS = {"Authorization": f"Bearer {AIRTABLE_API_KEY}",
           "Content-Type": "application/json"}

def push_record(table, record):
    try:
        requests.post(f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table}",
                      headers=HEADERS, json={"fields": record}, timeout=10)
    except Exception:
        pass

def log_kpi(engine, status):
    push_record("KPI_Log", {
        "Engine": engine,
        "Status": status,
        "Timestamp": datetime.datetime.utcnow().isoformat()
    })

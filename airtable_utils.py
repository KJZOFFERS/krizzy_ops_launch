import os, requests, datetime

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}

def push_record(table, record):
    """Create or update a record in Airtable."""
    try:
        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table}"
        r = requests.post(url, headers=HEADERS, json={"fields": record}, timeout=10)
        if r.status_code != 200:
            print(f"Airtable write failed: {r.text}")
        else:
            print(f"Airtable write success: {r.status_code}")
    except Exception as e:
        print(f"Airtable error: {e}")

def log_kpi(engine, status):
    """Log KPIs and status updates to Airtable."""
    fields = {
        "Engine": engine,
        "Status": status,
        "Timestamp": datetime.datetime.utcnow().isoformat()
    }
    push_record("KPI_Log", fields)

import os, json, logging, requests

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

def _headers():
    return {"Authorization": f"Bearer {AIRTABLE_API_KEY}", "Content-Type": "application/json"}

def fetch_table(table_name: str):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table_name}"
    r = requests.get(url, headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json().get("records", [])

def safe_airtable_write(table_name: str, record: dict):
    try:
        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table_name}"
        r = requests.post(url, headers=_headers(), data=json.dumps({"fields": record}), timeout=10)
        r.raise_for_status()
        return True
    except Exception as e:
        logging.error(f"Airtable write failed: {e}")
        return False

import requests, os

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("AIRTABLE_BASE_ID")

def push_record(table_name, data):
    url = f"https://api.airtable.com/v0/{BASE_ID}/{table_name}"
    headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}", "Content-Type": "application/json"}
    payload = {"records": [{"fields": data}]}
    r = requests.post(url, headers=headers, json=payload, timeout=20)
    r.raise_for_status()
    return r.json()

import os, time, requests

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("AIRTABLE_BASE_ID")

def write_record(table: str, fields: dict):
    """Simple Airtable insert."""
    url = f"https://api.airtable.com/v0/{BASE_ID}/{table}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"records": [{"fields": fields}]}
    r = requests.post(url, json=payload, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()

def upsert_record(table: str, uniq_field: str, uniq_value: str, fields: dict):
    """Update or insert row by unique field."""
    url = f"https://api.airtable.com/v0/{BASE_ID}/{table}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json",
    }
    params = {"filterByFormula": f"{{{uniq_field}}}='{uniq_value}'"}
    r = requests.get(url, headers=headers, params=params, timeout=10)
    r.raise_for_status()
    records = r.json().get("records", [])
    data = {"fields": {**fields, uniq_field: uniq_value, "ts": int(time.time())}}
    if records:
        rid = records[0]["id"]
        requests.patch(f"{url}/{rid}", headers=headers, json=data, timeout=10)
    else:
        requests.post(url, headers=headers, json={"records": [data]}, timeout=10)

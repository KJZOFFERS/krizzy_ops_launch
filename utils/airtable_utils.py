import os, requests

API_KEY = os.getenv("AIRTABLE_API_KEY")
BASE_ID = os.getenv("AIRTABLE_BASE_ID")

def write_record(table, fields):
    url = f"https://api.airtable.com/v0/{BASE_ID}/{table}"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {"records": [{"fields": fields}]}
    r = requests.post(url, headers=headers, json=data, timeout=10)
    return r.status_code

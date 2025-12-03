import os
import requests

BASE_ID = os.environ["AIRTABLE_BASE_ID"]
API_KEY = os.environ["AIRTABLE_API_KEY"]
API = "https://api.airtable.com/v0"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def read_records(table, formula=None):
    url = f"{API}/{BASE_ID}/{table}"
    params = {}
    if formula:
        params["filterByFormula"] = formula
    r = requests.get(url, headers=HEADERS, params=params)
    r.raise_for_status()
    return r.json().get("records", [])

def write_record(table, fields):
    url = f"{API}/{BASE_ID}/{table}"
    r = requests.post(url, headers=HEADERS, json={"fields": fields})
    r.raise_for_status()
    return r.json()

def update_record(table, record_id, fields):
    url = f"{API}/{BASE_ID}/{table}/{record_id}"
    r = requests.patch(url, headers=HEADERS, json={"fields": fields})
    r.raise_for_status()
    return r.json()

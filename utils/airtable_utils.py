import os
import requests

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

def airtable_write(table: str, record: dict):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table}"
    headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}", "Content-Type": "application/json"}
    requests.post(url, json={"fields": record}, headers=headers)


def write_record(table: str, fields: dict):
    """Compatibility shim used by data_extraction.py and kpi.py."""
    return airtable_write(table, fields)

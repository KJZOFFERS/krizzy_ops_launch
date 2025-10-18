import os, requests
from dotenv import load_dotenv
load_dotenv()

BASE_ID = os.getenv("AIRTABLE_BASE_ID")
KEY = os.getenv("AIRTABLE_API_KEY")
HEADERS = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

def add_record(table, fields):
    url = f"https://api.airtable.com/v0/{BASE_ID}/{table}"
    r = requests.post(url, headers=HEADERS, json={"fields": fields})
    return r.json()

def fetch_all(table):
    url = f"https://api.airtable.com/v0/{BASE_ID}/{table}"
    r = requests.get(url, headers=HEADERS)
    return r.json().get("records", [])

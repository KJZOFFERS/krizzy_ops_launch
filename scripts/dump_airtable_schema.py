import os
import json
import requests

BASE_ID = os.environ["AIRTABLE_BASE_ID"]
API_KEY = os.environ["AIRTABLE_API_KEY"]

url = f"https://api.airtable.com/v0/meta/bases/{BASE_ID}/tables"
r = requests.get(url, headers={"Authorization": f"Bearer {API_KEY}"})
r.raise_for_status()

open("schema.json", "w").write(json.dumps(r.json(), indent=2))
print("Wrote schema.json")

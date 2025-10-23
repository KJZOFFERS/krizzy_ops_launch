import requests, os, time
from discord_utils import send_error

def safe_write(table, data):
    url = f"https://api.airtable.com/v0/{os.environ['AIRTABLE_BASE_ID']}/{table}"
    headers = {
        "Authorization": f"Bearer {os.environ['AIRTABLE_API_KEY']}",
        "Content-Type": "application/json"
    }
    for _ in range(3):
        r = requests.post(url, headers=headers, json={"fields": data})
        if r.status_code == 200:
            return True
        time.sleep(3)
    send_error(f"Airtable write failed: {r.text}")

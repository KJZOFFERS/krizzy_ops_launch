import os
import requests
from datetime import datetime

# === Load environment variables ===
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")

# Verify keys on startup
if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
    raise ValueError("Missing Airtable API key or base ID environment variables")

# === Core Airtable function ===
def airtable_write(table_name: str, fields: dict):
    """Write a record to Airtable and return success/failure."""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{table_name}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json",
    }

    data = {"fields": fields}

    try:
        r = requests.post(url, headers=headers, json=data)
        r.raise_for_status()
        print(f"[{datetime.utcnow()}] Airtable write success: {r.status_code}")
        return r.json()
    except requests.exceptions.HTTPError as e:
        print(f"[{datetime.utcnow()}] Airtable write failed: {r.text}")
        return {"error": str(e), "response": r.text}
    except Exception as e:
        print(f"[{datetime.utcnow()}] Airtable write error: {e}")
        return {"error": str(e)}

# === Quick test ===
if __name__ == "__main__":
    # Ping test to confirm connection
    test_table = "KPI_Log"  # update with one of your real table names
    result = airtable_write(test_table, {"Test": "Ping"})
    print(result)

import os, time, requests

_BASE = os.getenv("AIRTABLE_BASE_ID", "")
_API = os.getenv("AIRTABLE_API_KEY", "")

def upsert(table: str, uniq_field: str, uniq_value: str, data: dict) -> None:
    """Upsert by uniq_field. Idempotent."""
    headers = {"Authorization": f"Bearer { _API }", "Content-Type": "application/json"}
    url = f"https://api.airtable.com/v0/{_BASE}/{table}"
    # find existing
    params = {"filterByFormula": f"{{{uniq_field}}}='{uniq_value}'"}
    r = requests.get(url, headers=headers, params=params, timeout=10)
    r.raise_for_status()
    recs = r.json().get("records", [])
    fields = {**data, uniq_field: uniq_value, "ts": int(time.time())}
    if recs:
        rid = recs[0]["id"]
        requests.patch(f"{url}/{rid}", headers=headers, json={"fields": fields}, timeout=10).raise_for_status()
    else:
        requests.post(url, headers=headers, json={"fields": fields}, timeout=10).raise_for_status()

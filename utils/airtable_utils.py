import json, os, urllib.parse, urllib.request

API_KEY = os.getenv("AIRTABLE_API_KEY", "")
BASE_ID = os.getenv("AIRTABLE_BASE_ID", "")

def _endpoint(table: str) -> str:
    return f"https://api.airtable.com/v0/{BASE_ID}/{urllib.parse.quote(table)}"

def _headers():
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

def list_records(table: str, formula: str | None = None, max_records: int = 10):
    params = {}
    if formula:
        params["filterByFormula"] = formula
    if max_records:
        params["pageSize"] = max_records
    url = _endpoint(table) + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers=_headers(), method="GET")
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    return data.get("records", [])

def _find_by_key(table: str, key_field: str, key_value: str):
    # Escape double quotes inside value
    val = str(key_value).replace('"', '\\"')
    formula = f'{{{key_field}}} = "{val}"'
    recs = list_records(table, formula=formula, max_records=1)
    return recs[0] if recs else None

def upsert_record(table: str, key_field: str, key_value: str, payload: dict):
    found = _find_by_key(table, key_field, key_value)
    if found:
        rec_id = found["id"]
        url = _endpoint(table) + "/" + rec_id
        body = json.dumps({"fields": payload}).encode("utf-8")
        req = urllib.request.Request(url, headers=_headers(), data=body, method="PATCH")
    else:
        url = _endpoint(table)
        body = json.dumps({"fields": payload}).encode("utf-8")
        req = urllib.request.Request(url, headers=_headers(), data=body, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


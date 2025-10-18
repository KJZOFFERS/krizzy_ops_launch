from airtable_utils import fetch_all
from discord_utils import post_ops
import datetime

def run_watchdog():
    tables = ["Leads_REI", "GovCon_Opportunities"]
    cleaned = 0
    for t in tables:
        records = fetch_all(t)
        for r in records:
            f = r["fields"]
            if not f.get("Source_URL") or not (f.get("Phone") or f.get("Email")):
                cleaned += 1
    post_ops(f"Watchdog scan completed {datetime.datetime.utcnow().isoformat()} | Invalid: {cleaned}")
    return cleaned

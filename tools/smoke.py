from __future__ import annotations

import os
import requests

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
DISCORD_WEBHOOK_OPS = os.getenv("DISCORD_WEBHOOK_OPS")
DISCORD_WEBHOOK_ERRORS = os.getenv("DISCORD_WEBHOOK_ERRORS")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_MESSAGING_SERVICE_SID = os.getenv("TWILIO_MESSAGING_SERVICE_SID")
SAM_SEARCH_API = os.getenv("SAM_SEARCH_API") or os.getenv("SAM_API")
FPDS_ATOM_FEED = os.getenv("FPDS_ATOM_FEED")


def main() -> int:
    ok = True

    # Airtable simple check: if keys present, attempt list bases via REST metadata (status 200/403 acceptable)
    if AIRTABLE_API_KEY and AIRTABLE_BASE_ID:
        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/KPI_Log?maxRecords=1"
        r = requests.get(
            url, headers={"Authorization": f"Bearer {AIRTABLE_API_KEY}"}, timeout=15
        )
        print("Airtable status:", r.status_code)
        ok = ok and (r.status_code in (200, 401, 403))

    # Discord
    if DISCORD_WEBHOOK_OPS:
        r = requests.post(
            DISCORD_WEBHOOK_OPS, json={"content": "smoke: ops ok"}, timeout=10
        )
        print("Discord OPS:", r.status_code)
        ok = ok and (r.status_code in (200, 204))
    if DISCORD_WEBHOOK_ERRORS:
        r = requests.post(
            DISCORD_WEBHOOK_ERRORS, json={"content": "smoke: errs ok"}, timeout=10
        )
        print("Discord ERR:", r.status_code)
        ok = ok and (r.status_code in (200, 204))

    # Twilio
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        from twilio.rest import Client

        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        try:
            acc = client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
            print("Twilio account fetched:", bool(acc.sid))
            ok = ok and bool(acc.sid)
        except Exception as e:  # noqa: BLE001
            print("Twilio fetch error:", e)
            ok = False

    # SAM/FPDS endpoints should return 200
    if SAM_SEARCH_API:
        r = requests.get(SAM_SEARCH_API, timeout=15)
        print("SAM:", r.status_code)
        ok = ok and (r.status_code == 200)
    if FPDS_ATOM_FEED:
        r = requests.get(FPDS_ATOM_FEED, timeout=15)
        print("FPDS:", r.status_code)
        ok = ok and (r.status_code == 200)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

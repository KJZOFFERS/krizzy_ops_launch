import os
import time
from datetime import datetime, timezone

from common import AirtableClient, notify_ops, log_crack, get_json_retry, get_text_retry

SAM_SEARCH_API = os.getenv("SAM_SEARCH_API", "")
FPDS_ATOM_FEED = os.getenv("FPDS_ATOM_FEED", "")
RUN_INTERVAL_MINUTES = int(os.getenv("RUN_INTERVAL_MINUTES", "15"))


def run_once(client: AirtableClient):
    report = {
        "airtable_active": True,
        "discord_ops_active": bool(os.getenv("DISCORD_WEBHOOK_OPS", "")),
        "sam_active": bool(SAM_SEARCH_API.strip()),
        "fpds_active": bool(FPDS_ATOM_FEED.strip()),
    }

    # SAM ping (optional)
    if SAM_SEARCH_API.strip():
        status, data = get_json_retry(SAM_SEARCH_API)
        if status != 200:
            raise RuntimeError(f"SAM HTTP {status}: {str(data)[:200]}")
        report["sam_records"] = data.get("totalRecords", 0)

    # FPDS ping (required if set)
    if FPDS_ATOM_FEED.strip():
        status, text = get_text_retry(FPDS_ATOM_FEED)
        if status != 200 or "<feed" not in text[:200]:
            raise RuntimeError(f"FPDS HTTP {status}: {text[:200]}")

    return report


def main():
    client = AirtableClient()
    notify_ops("OPS_HEALTH_SERVICE online.")

    while True:
        start = time.time()
        try:
            report = run_once(client)
            client.log_kpi("health_run", report)
            notify_ops(f"HEALTH ok: {report}")
        except Exception as e:
            log_crack("ops_health", str(e), client)

        elapsed = time.time() - start
        time.sleep(max(5, RUN_INTERVAL_MINUTES * 60 - int(elapsed)))


if __name__ == "__main__":
    main()

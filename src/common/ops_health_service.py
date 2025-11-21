"""OPS_HEALTH_SERVICE — Always-on heartbeat + system health monitor"""
import os
import time
from datetime import datetime, timezone

from src.common import AirtableClient, notify_ops, log_crack, get_json_retry, get_text_retry

SAM_SEARCH_API = os.getenv("SAM_SEARCH_API", "")
FPDS_ATOM_FEED = os.getenv("FPDS_ATOM_FEED", "")
RUN_INTERVAL_MINUTES = int(os.getenv("RUN_INTERVAL_MINUTES", "60"))


def run_health_check(client: AirtableClient):
    """Run system health checks"""
    report = {
        "airtable_active": True,
        "discord_ops_active": bool(os.getenv("DISCORD_WEBHOOK_OPS", "")),
        "sam_active": bool(SAM_SEARCH_API.strip()),
        "fpds_active": bool(FPDS_ATOM_FEED.strip()),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # SAM ping (optional)
    if SAM_SEARCH_API.strip():
        status, data = get_json_retry(SAM_SEARCH_API)
        if status == 200:
            report["sam_status"] = "ok"
            report["sam_records"] = data.get("totalRecords", 0)
        else:
            report["sam_status"] = f"error_{status}"

    # FPDS ping (optional)
    if FPDS_ATOM_FEED.strip():
        status, text = get_text_retry(FPDS_ATOM_FEED)
        if status == 200 and "<feed" in text[:500]:
            report["fpds_status"] = "ok"
        else:
            report["fpds_status"] = f"error_{status}"

    return report


def main():
    """Main health service loop"""
    print(f"[OPS_HEALTH] Starting service at {datetime.now(timezone.utc).isoformat()}")
    print(f"[OPS_HEALTH] Run interval: {RUN_INTERVAL_MINUTES} minutes")
    
    try:
        client = AirtableClient()
    except Exception as e:
        print(f"[OPS_HEALTH] FATAL: Airtable init failed: {e}")
        return
    
    notify_ops("✅ OPS_HEALTH_SERVICE online")

    while True:
        start = time.time()
        try:
            report = run_health_check(client)
            client.log_kpi("health_run", report)
            print(f"[OPS_HEALTH] {report}")
            notify_ops(f"💓 Health: {report.get('sam_status', 'N/A')} | {report.get('fpds_status', 'N/A')}")
        except Exception as e:
            print(f"[OPS_HEALTH] ERROR: {e}")
            log_crack("ops_health", str(e), client)

        elapsed = time.time() - start
        sleep_time = max(5, RUN_INTERVAL_MINUTES * 60 - int(elapsed))
        print(f"[OPS_HEALTH] Next run in {sleep_time}s")
        time.sleep(sleep_time)


if __name__ == "__main__":
    main()

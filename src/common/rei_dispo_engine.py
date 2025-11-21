"""REI_DISPO_ENGINE — Leads_REI → Buyer matching → SMS_Queue"""
import os
import time
from typing import Any, Dict, List

from src.common import AirtableClient, notify_ops, log_crack
from src.common.comms import twilio_available, twilio_send

RUN_INTERVAL_MINUTES = int(os.getenv("RUN_INTERVAL_MINUTES", "60"))

LEADS_TABLE = "Leads_REI"
BUYERS_TABLE = "Buyers"
MATCHES_TABLE = "REI_Matches"
SMS_QUEUE_TABLE = "SMS_Queue"


def simple_match(lead_fields: Dict[str, Any], buyer_fields: Dict[str, Any]) -> bool:
    """Simple keyword-based matching"""
    lead_text = " ".join([str(v) for v in lead_fields.values() if isinstance(v, str)]).lower()
    buyer_text = " ".join([str(v) for v in buyer_fields.values() if isinstance(v, str)]).lower()
    if not lead_text or not buyer_text:
        return False
    return any(tok in buyer_text for tok in lead_text.split()[:5])


def run_rei_engine(client: AirtableClient):
    """Main engine execution"""
    print(f"[REI] Starting run at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    leads = client.get_table(LEADS_TABLE).all(max_records=50)
    buyers = client.get_table(BUYERS_TABLE).all(max_records=200)
    
    print(f"[REI] Processing {len(leads)} leads, {len(buyers)} buyers")

    matches = 0
    sms_sent = 0
    sms_queued = 0

    for lead in leads:
        lf = lead.get("fields", {})
        for buyer in buyers:
            bf = buyer.get("fields", {})
            if not simple_match(lf, bf):
                continue

            matches += 1
            ts = time.strftime("%Y-%m-%d %H:%M:%S")

            client.safe_upsert(
                MATCHES_TABLE,
                {
                    "Lead ID": lead.get("id"),
                    "Buyer ID": buyer.get("id"),
                    "Lead Snapshot": str(lf)[:10000],
                    "Buyer Snapshot": str(bf)[:10000],
                    "Timestamp": ts,
                    "Status": "matched",
                },
                match_fields=["Lead ID", "Buyer ID"],
                typecast=False,
            )

            phone = bf.get("Phone") or bf.get("Phone Number") or ""
            msg = "Deal match found. Reply YES for details."

            if phone and twilio_available():
                try:
                    if twilio_send(phone, msg):
                        sms_sent += 1
                    else:
                        sms_queued += 1
                except Exception:
                    sms_queued += 1
            else:
                sms_queued += 1

            # Always queue a record for tracking
            client.safe_upsert(
                SMS_QUEUE_TABLE,
                {
                    "Buyer": bf.get("Name") or bf.get("Buyer Name"),
                    "Phone": phone,
                    "Message": msg,
                    "Status": "sent" if (phone and twilio_available()) else "queued",
                    "Timestamp": ts,
                },
                match_fields=["Timestamp", "Buyer"],
                typecast=False,
            )

    return {
        "leads_fetched": len(leads),
        "buyers_fetched": len(buyers),
        "matches": matches,
        "sms_sent": sms_sent,
        "sms_queued": sms_queued,
        "twilio_active": twilio_available(),
    }


def main():
    """Main service loop"""
    print(f"[REI] Starting service at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[REI] Run interval: {RUN_INTERVAL_MINUTES} minutes")
    print(f"[REI] Twilio: {'ENABLED' if twilio_available() else 'DISABLED (queue only)'}")
    
    try:
        client = AirtableClient()
    except Exception as e:
        print(f"[REI] FATAL: Airtable init failed: {e}")
        return
    
    notify_ops("✅ REI_DISPO_ENGINE online")

    while True:
        start = time.time()
        try:
            stats = run_rei_engine(client)
            client.log_kpi("rei_run", stats)
            print(f"[REI] {stats}")
            notify_ops(f"🏠 REI: {stats['matches']} matches | {stats['sms_sent']} sent | {stats['sms_queued']} queued")
        except Exception as e:
            print(f"[REI] ERROR: {e}")
            log_crack("rei_engine", str(e), client)

        elapsed = time.time() - start
        sleep_time = max(5, RUN_INTERVAL_MINUTES * 60 - int(elapsed))
        print(f"[REI] Next run in {sleep_time}s")
        time.sleep(sleep_time)


if __name__ == "__main__":
    main()

# src/rei_dispo_engine.py

"""REI_DISPO_ENGINE — Leads_REI → Buyer matching → SMS_Queue"""
import os
import time
from typing import Any, Dict, List

from src.common import AirtableClient
from src.common.comms import twilio_available, twilio_send
from src.ops import send_ops, send_crack, guard_engine

RUN_INTERVAL_MINUTES = int(os.getenv("RUN_INTERVAL_MINUTES", "15"))

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


@guard_engine("rei_engine", max_consecutive_failures=5, disable_seconds=600)
def run_rei_cycle(client: AirtableClient) -> Dict[str, Any]:
    """Main engine execution - one cycle"""
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

            try:
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
            except Exception as e:
                send_crack("rei_engine", f"Match record failed: {e}", {"lead_id": lead.get("id")})
                continue

            phone = bf.get("Phone") or bf.get("Phone Number") or ""
            msg = "Deal match found. Reply YES for details."

            sms_status = "queued"
            if phone and twilio_available():
                try:
                    if twilio_send(phone, msg):
                        sms_sent += 1
                        sms_status = "sent"
                    else:
                        sms_queued += 1
                except Exception as e:
                    sms_queued += 1
                    send_crack("rei_engine", f"SMS send failed: {e}", {"phone": phone})
            else:
                sms_queued += 1

            # Always queue a record for tracking
            try:
                client.safe_upsert(
                    SMS_QUEUE_TABLE,
                    {
                        "Buyer": bf.get("Name") or bf.get("Buyer Name"),
                        "Phone": phone,
                        "Message": msg,
                        "Status": sms_status,
                        "Timestamp": ts,
                    },
                    match_fields=["Timestamp", "Buyer"],
                    typecast=False,
                )
            except Exception as e:
                send_crack("rei_engine", f"SMS queue record failed: {e}")

    stats = {
        "leads_fetched": len(leads),
        "buyers_fetched": len(buyers),
        "matches": matches,
        "sms_sent": sms_sent,
        "sms_queued": sms_queued,
        "twilio_active": twilio_available(),
    }
    
    return stats


def main():
    """Main service loop"""
    print(f"[REI] Starting service at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[REI] Run interval: {RUN_INTERVAL_MINUTES} minutes")
    print(f"[REI] Twilio: {'ENABLED' if twilio_available() else 'DISABLED (queue only)'}")
    
    try:
        client = AirtableClient()
    except Exception as e:
        print(f"[REI] FATAL: Airtable init failed: {e}")
        send_crack("rei_engine", f"Airtable init failed: {e}")
        return
    
    send_ops("✅ REI_DISPO_ENGINE online")

    while True:
        start = time.time()
        
        stats = run_rei_cycle(client)
        
        if stats:
            client.log_kpi("rei_run", stats)
            print(f"[REI] {stats}")
            send_ops(f"🏠 REI: {stats['matches']} matches | {stats['sms_sent']} sent | {stats['sms_queued']} queued")

        elapsed = time.time() - start
        sleep_time = max(5, RUN_INTERVAL_MINUTES * 60 - int(elapsed))
        print(f"[REI] Next run in {sleep_time}s")
        time.sleep(sleep_time)


if __name__ == "__main__":
    main()

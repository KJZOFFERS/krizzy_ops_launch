import os
import time
from typing import Any, Dict, List

from common import AirtableClient, notify_ops, log_crack
from common.comms import discord_post  # optional if you still want direct post
from common.comms import DISCORD_WEBHOOK_OPS  # just for visibility
from common.comms import notify_ops
from common.comms import notify_error
from common.comms import log_crack as comms_log_crack
from common.comms import notify_ops
from common.comms import notify_error
from common.comms import log_crack as comms_log_crack

# Twilio optional (no new vars)
from common.comms import twilio_available, twilio_send

RUN_INTERVAL_MINUTES = int(os.getenv("RUN_INTERVAL_MINUTES", "15"))

LEADS_TABLE = "Leads_REI"
BUYERS_TABLE = "Buyers"
MATCHES_TABLE = "REI_Matches"
SMS_QUEUE_TABLE = "SMS_Queue"


def simple_match(lead_fields: Dict[str, Any], buyer_fields: Dict[str, Any]) -> bool:
    lead_text = " ".join([str(v) for v in lead_fields.values() if isinstance(v, str)]).lower()
    buyer_text = " ".join([str(v) for v in buyer_fields.values() if isinstance(v, str)]).lower()
    if not lead_text or not buyer_text:
        return False
    return any(tok in buyer_text for tok in lead_text.split()[:5])


def run_once(client: AirtableClient):
    leads = client.get_table(LEADS_TABLE).all(max_records=50)
    buyers = client.get_table(BUYERS_TABLE).all(max_records=200)

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
                match_fields=["Timestamp", "Lead ID"],
                typecast=False,
            )

            phone = bf.get("Phone") or bf.get("Phone Number") or ""
            msg = "Deal match found. Reply YES for details."

            if phone and twilio_available():
                try:
                    twilio_send(phone, msg)
                    sms_sent += 1
                except Exception:
                    sms_queued += 1
            else:
                sms_queued += 1

            # Always queue a record schema-safely for tracking
            client.safe_upsert(
                SMS_QUEUE_TABLE,
                {
                    "Buyer": bf.get("Name") or bf.get("Buyer Name"),
                    "Phone": phone,
                    "Message": msg,
                    "Status": "sent" if twilio_available() else "queued",
                    "Timestamp": ts,
                },
                match_fields=["Timestamp"],
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
    client = AirtableClient()
    notify_ops("REI_DISPO_ENGINE online.")

    while True:
        start = time.time()
        try:
            stats = run_once(client)
            client.log_kpi("rei_run", stats)
            notify_ops(f"REI ok: {stats}")
        except Exception as e:
            log_crack("rei_engine", str(e), client)

        elapsed = time.time() - start
        time.sleep(max(5, RUN_INTERVAL_MINUTES * 60 - int(elapsed)))


if __name__ == "__main__":
    main()

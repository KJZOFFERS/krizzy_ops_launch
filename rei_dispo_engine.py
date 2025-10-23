import time
from airtable_utils import safe_write
from discord_utils import send_ops

def start_rei_dispo():
    while True:
        leads = [{"name": "Cash Buyer LLC", "market": "TX"}]
        for lead in leads:
            safe_write("Leads_REI", lead)
        send_ops("REI_DISPO_ENGINE cycle complete ✅")
        time.sleep(3600)

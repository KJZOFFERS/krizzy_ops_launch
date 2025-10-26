import asyncio, requests, os
fimport time
from utils.airtable_utils import push_record
from utils.discord_utils import post_to_discord

def run_rei_dispo():
    while True:
        try:
            lead = {"Property": "Test Deal", "Status": "New"}
            push_record("Leads_REI", lead)
            post_to_discord("ops", f"REI_DISPO cycle executed: {lead}")
            time.sleep(60)
        except Exception as e:
            post_to_discord("errors", f"REI_DISPO error: {e}")
            time.sleep(30)

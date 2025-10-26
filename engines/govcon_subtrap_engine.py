import time
from utils.airtable_utils import push_record
from utils.discord_utils import post_to_discord

def run_govcon_subtrap():
    while True:
        try:
            opp = {"Solicitation": "SAM Test", "NAICS": "541611"}
            push_record("GovCon_Opportunities", opp)
            post_to_discord("ops", f"GOVCON_SUBTRAP cycle executed: {opp}")
            time.sleep(120)
        except Exception as e:
            post_to_discord("errors", f"GOVCON_SUBTRAP error: {e}")
            time.sleep(60)

import os, requests, datetime
import time
from airtable_utils import safe_write
from discord_utils import send_ops

def start_govcon():
    while True:
        opps = [{"solicitation": "12345", "title": "Facility Maintenance"}]
        for opp in opps:
            safe_write("GovCon_Opportunities", opp)
        send_ops("GOVCON_SUBTRAP_ENGINE cycle complete ✅")
        time.sleep(10800)

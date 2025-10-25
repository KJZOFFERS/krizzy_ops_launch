from utils.airtable_utils import write_record
from utils.discord_utils import send_discord_message

def log_kpi(event, data):
    payload = {"Event": event, **data}
    write_record("KPI_Log", payload)
    send_discord_message(f"KPI event: {event} → {data}", "ops")

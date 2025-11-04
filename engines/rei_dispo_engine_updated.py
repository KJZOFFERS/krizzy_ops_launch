from utils import list_records, kpi_log
from utils.discord_utils import post_ops
from matching import match_buyers_to_lead
import os

# Table names and margin threshold from environment variables (with defaults)
LEADS_TABLE = os.getenv("AT_TABLE_LEADS_REI", "Leads_REI")
BUYERS_TABLE = os.getenv("AT_TABLE_BUYERS", "Buyers")
MIN_MARGIN = float(os.getenv("REI_MIN_MARGIN", 0.15))  # 15% default


def loop_rei():
    """
    REI Dispo Engine

    - Reads leads and buyers from Airtable tables.
    - Computes the profit margin for each lead (ARV - Ask) / ARV.
    - Filters out leads below the minimum margin.
    - Matches buyers by zip and budget using matching.match_buyers_to_lead.
    - Sends a formatted message to Discord for each qualified deal.
    - Logs the event to the KPI table.
    """
    leads = list_records(LEADS_TABLE)
    buyers = list_records(BUYERS_TABLE)
    for lead in leads:
        fields = lead.get("fields", {})
        key = fields.get("key")
        address = fields.get("address")
        arv = fields.get("ARV")
        ask = fields.get("Ask")
        zip_code = fields.get("address", "")[-5:] if fields.get("address") else None
        # Require both ARV and Ask for margin calculation
        if not arv or not ask:
            continue
        try:
            margin = (float(arv) - float(ask)) / float(arv)
        except Exception:
            continue
        # Skip leads below the minimum margin
        if margin < MIN_MARGIN:
            continue
        # Match buyers by zip and budget
        matched_buyers = match_buyers_to_lead(zip_code, float(ask), buyers)
        # Send a formatted message to Discord
        message = (
            f"**REI Qualified Deal**\n"
            f"Address: `{address}`\n"
            f"Ask: ${float(ask):,.0f}\n"
            f"ARV: ${float(arv):,.0f}\n"
            f"Margin: {margin:.1%}\n"
            f"Zip: {zip_code}\n"
            f"Matched Buyers: {len(matched_buyers)}"
        )
        post_ops(message)
        # Log to KPI table
        kpi_log(
            engine="REI_Dispo",
            action="Qualified Deal",
            record_id=key,
            details={"margin": margin, "matched_buyers": len(matched_buyers)}
        )

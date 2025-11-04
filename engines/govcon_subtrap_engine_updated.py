from utils import list_records, kpi_log
from utils.discord_utils import post_ops
import os

# Table name and filters from environment variables
OPP_TABLE = os.getenv("AT_TABLE_GOVCON", "GovCon_Opportunities")
NAICS_WHITELIST = os.getenv("NAICS_WHITELIST", "").replace(" ", "").split(",")
MAX_DAYS = int(os.getenv("GOVCON_POSTED_DAYS", 14))  # default: 14 days


def loop_govcon():
    """
    GovCon Sub-Trap Engine

    - Reads opportunities from Airtable.
    - Filters by NAICS code whitelist and maximum days until deadline.
    - Sends a formatted message to Discord for each qualified opportunity.
    - Logs the event to the KPI table.
    """
    opportunities = list_records(OPP_TABLE)
    for opp in opportunities:
        fields = opp.get("fields", {})
        key = fields.get("key")
        name = fields.get("Opportunity Name")
        agency = fields.get("Agency")
        value = fields.get("Total Value")
        naics = str(fields.get("NAICS Code", "")).replace(" ", "").split(",")
        days = fields.get("Days Until Deadline")
        # Filter by NAICS whitelist
        if not set(naics).intersection(NAICS_WHITELIST):
            continue
        # Filter by maximum days
        if days is not None and days > MAX_DAYS:
            continue
        # Send message to Discord
        message = (
            f"**GovCon Qualified Opportunity**\n"
            f"Name: `{name}`\n"
            f"Agency: {agency}\n"
            f"Value: ${float(value):,.0f}\n"
            f"NAICS: {', '.join(naics)}\n"
            f"Days Left: {days}"
        )
        post_ops(message)
        # Log to KPI table
        kpi_log(
            engine="GovCon_SubTrap",
            action="Qualified Opportunity",
            record_id=key,
            details={"days_left": days}
        )

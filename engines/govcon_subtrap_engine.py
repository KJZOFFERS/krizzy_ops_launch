from utils import list_records, kpi_log
from utils.discord_utils import post_ops
import os

OPP_TABLE = os.getenv("AT_TABLE_GOVCON", "GovCon_Opportunities")
NAICS_WHITELIST = os.getenv("NAICS_WHITELIST", "").replace(" ", "").split(",")
MAX_DAYS = int(os.getenv("GOVCON_POSTED_DAYS", 14))


def loop_govcon():
    opps = list_records(OPP_TABLE)

    for opp in opps:
        f = opp.get("fields", {})
        key = f.get("key")
        name = f.get("Opportunity Name")
        agency = f.get("Agency")
        value = f.get("Total Value")
        naics = str(f.get("NAICS Code", "")).replace(" ", "").split(",")
        days = f.get("Days Until Deadline")

        if not set(naics).intersection(NAICS_WHITELIST):
            continue
        if days and days > MAX_DAYS:
            continue

        post_ops(f"""
**GovCon Qualified Opportunity**
Name: `{name}`
Agency: {agency}
Value: ${value:,.0f}
NAICS: {', '.join(naics)}
Days Left: {days}
""")

        kpi_log(
            engine="GovCon_SubTrap",
            action="Qualified Opportunity",
            record_id=key,
            details={"days_left": days}
        )

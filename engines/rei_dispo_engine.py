from utils import list_records, kpi_log
from utils.discord_utils import post_ops
from utils.matching import match_buyers_to_lead
import os

LEADS_TABLE = os.getenv("AT_TABLE_LEADS_REI", "Leads_REI")
BUYERS_TABLE = os.getenv("AT_TABLE_BUYERS", "Buyers")
MIN_MARGIN = float(os.getenv("REI_MIN_MARGIN", 0.15))  # 15% default


def loop_rei():
    leads = list_records(LEADS_TABLE)
    buyers = list_records(BUYERS_TABLE)

    for lead in leads:
        f = lead.get("fields", {})
        key = f.get("key")
        address = f.get("address")
        arv = f.get("ARV")
        ask = f.get("Ask")
        zip_code = f.get("address", "")[-5:] if f.get("address") else None

        if not arv or not ask:
            continue

        try:
            margin = (float(arv) - float(ask)) / float(arv)
        except:
            continue

        if margin < MIN_MARGIN:
            continue

        matched = match_buyers_to_lead(zip_code, float(ask), buyers)

        post_ops(f"""
**REI Qualified Deal**
Address: `{address}`
Ask: ${ask:,.0f}
ARV: ${arv:,.0f}
Margin: {margin:.1%}
Zip: {zip_code}
Matched Buyers: {len(matched)}
""")

        kpi_log(
            engine="REI_Dispo",
            action="Qualified Deal",
            record_id=key,
            details={"margin": margin, "matched_buyers": len(matched)}
        )

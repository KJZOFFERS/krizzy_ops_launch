import os, requests, datetime
from airtable_utils import add_record, fetch_all
from discord_utils import post_ops, post_error
from dotenv import load_dotenv
load_dotenv()

SAM_API = os.getenv("SAM_API")
SAM_KEY = os.getenv("SAM_API_KEY")

def run_govcon():
    params = {
        "limit": 20,
        "api_key": SAM_KEY,
        "sort": "-publishDate",
        "postedFrom": (datetime.date.today() - datetime.timedelta(days=14)).isoformat(),
        "postedTo": datetime.date.today().isoformat()
    }
    try:
        r = requests.get(SAM_API, params=params, timeout=15)
        data = r.json().get("opportunitiesData", [])
    except Exception as e:
        post_error(f"SAM.gov pull failed: {e}")
        return 0

    existing = fetch_all("GovCon_Opportunities")
    existing_ids = {r["fields"].get("Solicitation #") for r in existing}

    new_records = []
    for d in data:
        sid = d.get("solicitationNumber")
        if not sid or sid in existing_ids:
            continue
        officer = d.get("officers", [{}])[0]
        email = officer.get("email", "")
        if not email:
            continue
        new_records.append({
            "Solicitation #": sid,
            "Title": d.get("title", ""),
            "NAICS": d.get("naicsCode", ""),
            "Due_Date": d.get("responseDate", ""),
            "Officer": officer.get("fullName", ""),
            "Email": email,
            "Status": d.get("type", ""),
            "Link": d.get("uiLink", ""),
            "Timestamp": datetime.datetime.utcnow().isoformat()
        })

    for n in new_records:
        add_record("GovCon_Opportunities", n)
    post_ops(f"GovCon loop added {len(new_records)} verified solicitations.")
    return len(new_records)

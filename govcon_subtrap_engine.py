"""GovCon opportunity engine with SAM.gov and FPDS integration."""

import os
import datetime
import hashlib
from typing import List, Dict, Any, Optional
import requests
from airtable_utils import safe_airtable_write
from discord_utils import post_ops, post_err
import kpi


SAM_SEARCH_API = os.getenv("SAM_SEARCH_API")
FPDS_ATOM_FEED = os.getenv("FPDS_ATOM_FEED")
NAICS_WHITELIST = os.getenv("NAICS_WHITELIST", "").split(",")
NAICS_WHITELIST = [n.strip() for n in NAICS_WHITELIST if n.strip()]
UEI = os.getenv("UEI", "")
CAGE_CODE = os.getenv("CAGE_CODE", "")


def _is_within_7_days(due_date_str: str) -> bool:
    """Check if due date is within 7 days."""
    if not due_date_str:
        return False

    try:
        due_date = datetime.datetime.fromisoformat(
            due_date_str.replace("Z", "+00:00")
        )
        today = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        days_until_due = (due_date - today).days
        return 0 <= days_until_due <= 7
    except Exception:
        return False


def _matches_naics(naics_code: str) -> bool:
    """Check if NAICS code matches whitelist."""
    if not NAICS_WHITELIST or not any(NAICS_WHITELIST):
        return True
    return any(naics_code.startswith(allowed) for allowed in NAICS_WHITELIST)


def _is_combined_synopsis(notice_type: str) -> bool:
    """Check if notice is Combined Synopsis/Solicitation."""
    combined_types = [
        "Combined Synopsis/Solicitation",
        "Presolicitation",
        "Solicitation",
    ]
    return any(t.lower() in notice_type.lower() for t in combined_types)


def fetch_sam_opportunities() -> List[Dict[str, Any]]:
    """Fetch opportunities from SAM.gov API."""
    if not SAM_SEARCH_API:
        post_err("SAM_SEARCH_API not configured")
        return []

    params = {
        "limit": 100,
        "postedFrom": (datetime.date.today() - datetime.timedelta(days=14)).isoformat(),
        "postedTo": datetime.date.today().isoformat(),
        "ptype": "o",
    }

    try:
        response = requests.get(SAM_SEARCH_API, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("opportunitiesData", [])
    except Exception as e:
        post_err(f"SAM.gov pull failed: {e}")
        kpi.kpi_push("error", {"source": "sam_gov", "error": str(e)})
        return []


def fetch_fpds_opportunities() -> List[Dict[str, Any]]:
    """Fetch opportunities from FPDS ATOM feed."""
    if not FPDS_ATOM_FEED:
        return []

    import xml.etree.ElementTree as ET

    try:
        response = requests.get(FPDS_ATOM_FEED, timeout=30)
        response.raise_for_status()
        root = ET.fromstring(response.text)

        opportunities = []
        for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry")[:50]:
            title_elem = entry.find("{http://www.w3.org/2005/Atom}title")
            link_elem = entry.find("{http://www.w3.org/2005/Atom}link")
            updated_elem = entry.find("{http://www.w3.org/2005/Atom}updated")

            title = title_elem.text if title_elem is not None else ""
            link = link_elem.get("href", "") if link_elem is not None else ""
            updated = updated_elem.text if updated_elem is not None else ""

            opportunities.append({
                "title": title,
                "uiLink": link,
                "responseDeadLine": updated,
                "solicitationNumber": hashlib.sha256(link.encode()).hexdigest()[:16],
                "type": "FPDS",
                "naicsCode": "",
            })

        return opportunities
    except Exception as e:
        post_err(f"FPDS pull failed: {e}")
        kpi.kpi_push("error", {"source": "fpds", "error": str(e)})
        return []


def build_bid_pack(opp: Dict[str, Any]) -> Dict[str, Any]:
    """Build bid pack JSON from opportunity data."""
    solicitation_number = opp.get("solicitationNumber", "")
    naics_code = opp.get("naicsCode", "")
    due_date = opp.get("responseDeadLine", "")
    notice_type = opp.get("type", "")

    officers = opp.get("pointOfContact", []) or opp.get("officers", [])
    if isinstance(officers, list) and officers:
        officer = officers[0]
    else:
        officer = {}

    return {
        "Solicitation_Number": solicitation_number,
        "Title": opp.get("title", ""),
        "NAICS": naics_code,
        "Due_Date": due_date,
        "Notice_Type": notice_type,
        "Officer_Name": officer.get("fullName", ""),
        "Officer_Email": officer.get("email", ""),
        "Officer_Phone": officer.get("phone", ""),
        "Link": opp.get("uiLink", ""),
        "Description": opp.get("description", "")[:500],
        "UEI": UEI,
        "CAGE_CODE": CAGE_CODE,
        "Timestamp": datetime.datetime.utcnow().isoformat(),
    }


def run_govcon() -> int:
    """
    Run GovCon opportunity engine.

    Returns:
        Number of new opportunities added
    """
    kpi.kpi_push("cycle_start", {"engine": "govcon_subtrap"})

    sam_opps = fetch_sam_opportunities()
    fpds_opps = fetch_fpds_opportunities()
    all_opps = sam_opps + fpds_opps

    filtered_opps = []
    for opp in all_opps:
        naics_code = opp.get("naicsCode", "")
        due_date = opp.get("responseDeadLine", "")
        notice_type = opp.get("type", "")

        if not _matches_naics(naics_code):
            continue

        if not _is_within_7_days(due_date):
            continue

        if not _is_combined_synopsis(notice_type):
            continue

        filtered_opps.append(opp)

    added_count = 0
    for opp in filtered_opps:
        bid_pack = build_bid_pack(opp)

        if not bid_pack.get("Officer_Email"):
            continue

        result = safe_airtable_write(
            "GovCon_Opportunities",
            bid_pack,
            key_fields=["Solicitation_Number"]
        )
        if result:
            added_count += 1

    post_ops(f"GovCon loop added {added_count} verified solicitations.")
    kpi.kpi_push("cycle_end", {"engine": "govcon_subtrap", "opportunities_added": added_count})

    return added_count

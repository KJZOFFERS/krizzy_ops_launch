"""REI disposition engine with seller/buyer enrichment and deduplication."""

import os
import hashlib
import datetime
from typing import List, Dict, Any
import requests
from airtable_utils import safe_airtable_write, fetch_all
from discord_utils import post_ops, post_err
from twilio_utils import send_msg
import kpi


ZILLOW_SEARCH = "https://www.zillow.com/homes/for_sale/?format=json"
CRAIGSLIST_SEARCH = "https://www.craigslist.org/search/rea?format=rss"


def _hash_contact(phone: str = "", email: str = "") -> str:
    """Generate hash for phone/email deduplication."""
    contact = f"{phone}|{email}".lower().strip()
    return hashlib.sha256(contact.encode()).hexdigest()[:16]


def parse_zillow() -> List[Dict[str, Any]]:
    """Parse Zillow search results."""
    try:
        response = requests.get(ZILLOW_SEARCH, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        post_err(f"Zillow pull failed: {e}")
        kpi.kpi_push("error", {"source": "zillow", "error": str(e)})
        return []

    leads = []
    for item in data.get("props", [])[:20]:
        if not item.get("address") or not item.get("price"):
            continue

        source_id = item.get("zpid", "") or item.get("id", "")
        phone = item.get("brokerPhone", "")
        email = item.get("brokerEmail", "")

        leads.append({
            "source_id": str(source_id),
            "contact_hash": _hash_contact(phone, email),
            "Address": item.get("address"),
            "City": item.get("city", ""),
            "State": item.get("state", ""),
            "Zip": str(item.get("zipcode", "")),
            "Price": str(item.get("price", "")),
            "ARV": str(item.get("price", "")),
            "Agent": item.get("brokerName", ""),
            "Phone": phone,
            "Email": email,
            "Source_URL": f"https://www.zillow.com{item.get('detailUrl', '')}",
            "Source": "Zillow",
            "Timestamp": datetime.datetime.utcnow().isoformat(),
        })

    return leads


def parse_craigslist() -> List[Dict[str, Any]]:
    """Parse Craigslist RSS feed."""
    import xml.etree.ElementTree as ET

    leads = []
    try:
        response = requests.get(CRAIGSLIST_SEARCH, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.text)

        for item in root.findall(".//item")[:10]:
            source_url = item.findtext("link", "")
            source_id = hashlib.sha256(source_url.encode()).hexdigest()[:16]

            leads.append({
                "source_id": source_id,
                "contact_hash": _hash_contact(),
                "Address": item.findtext("title", ""),
                "City": "",
                "State": "",
                "Zip": "",
                "Price": "",
                "ARV": "",
                "Agent": "",
                "Phone": "",
                "Email": "",
                "Source_URL": source_url,
                "Source": "Craigslist",
                "Timestamp": datetime.datetime.utcnow().isoformat(),
            })
    except Exception as e:
        post_err(f"Craigslist parse failed: {e}")
        kpi.kpi_push("error", {"source": "craigslist", "error": str(e)})

    return leads


def run_rei() -> int:
    """
    Run REI disposition engine.

    Returns:
        Number of new leads added
    """
    kpi.kpi_push("cycle_start", {"engine": "rei_dispo"})

    zillow_leads = parse_zillow()
    craigslist_leads = parse_craigslist()
    all_leads = zillow_leads + craigslist_leads

    valid_leads = [
        lead for lead in all_leads
        if lead.get("Phone") or lead.get("Email")
    ]

    added_count = 0
    for lead in valid_leads:
        result = safe_airtable_write(
            "Leads_REI",
            lead,
            key_fields=["source_id", "contact_hash"]
        )
        if result:
            added_count += 1

    post_ops(f"REI loop added {added_count} verified leads.")
    kpi.kpi_push("cycle_end", {"engine": "rei_dispo", "leads_added": added_count})

    return added_count

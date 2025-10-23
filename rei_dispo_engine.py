from __future__ import annotations

import datetime
import json
from typing import Any, Dict, List

import requests
from airtable_utils import compute_contact_hash, fetch_all, safe_airtable_write
from discord_utils import post_err, post_ops
from llm_router import enrich_text
from twilio_utils import send_msg

# Zillow & Craigslist scrapers use their public RSS/JSON feeds.
ZILLOW_SEARCH = "https://www.zillow.com/homes/for_sale/?format=json"
CRAIGSLIST_SEARCH = "https://www.craigslist.org/search/rea?format=rss"

def parse_zillow() -> List[Dict[str, Any]]:
    try:
        data = requests.get(ZILLOW_SEARCH, timeout=10).json()
    except Exception as e:  # noqa: BLE001
        post_err(f"Zillow pull failed: {e}")
        return []

    leads = []
    for item in data.get("props", [])[:20]:
        if not item.get("address") or not item.get("price"):
            continue
        leads.append({
            "Address": item.get("address"),
            "City": item.get("city"),
            "State": item.get("state"),
            "Zip": item.get("zipcode"),
            "Price": item.get("price"),
            "ARV": item.get("price"),  # placeholder for deterministic mode
            "Agent": item.get("brokerName", ""),
            "Phone": item.get("brokerPhone", ""),
            "Email": item.get("brokerEmail", ""),
            "Source_URL": f"https://www.zillow.com{item.get('detailUrl','')}",
            "Timestamp": datetime.datetime.utcnow().isoformat()
        })
    return leads

def parse_craigslist() -> List[Dict[str, Any]]:
    import xml.etree.ElementTree as ET
    leads = []
    try:
        r = requests.get(CRAIGSLIST_SEARCH, timeout=10)
        root = ET.fromstring(r.text)
        for item in root.findall(".//item")[:10]:
            leads.append({
                "Address": item.findtext("title"),
                "City": "",
                "State": "",
                "Zip": "",
                "Price": "",
                "ARV": "",
                "Agent": "",
                "Phone": "",
                "Email": "",
                "Source_URL": item.findtext("link"),
                "Timestamp": datetime.datetime.utcnow().isoformat()
            })
    except Exception as e:  # noqa: BLE001
        post_err(f"Craigslist parse failed: {e}")
    return leads

def deduplicate(new: List[Dict[str, Any]], existing: List[Dict[str, Any]]):
    existing_keys = set()
    for r in existing:
        f = r.get("fields", {})
        key = f.get("source_id") or f.get("Source_URL")
        if key:
            existing_keys.add(key)
    out = []
    for x in new:
        key = x.get("Source_URL")
        if key and key not in existing_keys:
            out.append(x)
    return out

def run_rei() -> int:
    z = parse_zillow()
    c = parse_craigslist()
    leads = z + c
    existing = fetch_all("Leads_REI")
    clean = [x for x in deduplicate(leads, existing) if x.get("Phone") or x.get("Email")]

    added = 0
    for lead in clean:
        # enrichment
        prompt = json.dumps({"address": lead.get("Address"), "city": lead.get("City"), "state": lead.get("State")})
        enrichment = enrich_text(f"Generate a concise investment summary for: {prompt}")
        lead["Summary"] = enrichment or ""

        contact_hash = compute_contact_hash(lead.get("Phone"), lead.get("Email"))
        record = {
            **lead,
            "source_id": lead.get("Source_URL"),
            "contact_hash": contact_hash,
            "Timestamp": datetime.datetime.utcnow().isoformat(),
        }
        safe_airtable_write("Leads_REI", record, key_fields=["source_id"])  # idempotent
        added += 1

        # Optional buyer outreach via Twilio if phone exists
        phone = lead.get("Phone")
        if phone:
            send_msg(
                to=phone,
                body_variants=[
                    "Hi, saw your listing. Are you open to an all-cash offer?",
                    "Quick note: Interested buyer for your property. Cash, fast close—open to chat?",
                    "Investor inquiry: would you consider a straightforward cash sale?",
                ],
            )

        # Buyer record if agent contact exists
        agent = (lead.get("Agent") or "").strip()
        buyer_phone = (lead.get("Phone") or "").strip()
        buyer_email = (lead.get("Email") or "").strip()
        if agent and (buyer_phone or buyer_email):
            buyer_record = {
                "Name": agent,
                "Phone": buyer_phone,
                "Email": buyer_email,
                "Source_URL": lead.get("Source_URL"),
                "contact_hash": compute_contact_hash(buyer_phone, buyer_email),
                "source_id": lead.get("Source_URL") + "|buyer",
                "Timestamp": datetime.datetime.utcnow().isoformat(),
            }
            safe_airtable_write("Buyers", buyer_record, key_fields=["contact_hash"])  # idempotent

    post_ops(f"REI loop added {added} verified leads.")
    return added

from __future__ import annotations

import datetime
import os
import random
import time
from typing import Any, Dict, Iterable, List

import requests

from airtable_utils import fetch_all, safe_airtable_write
from discord_utils import post_err, post_ops

# Required env names
NAICS_WHITELIST = {x.strip() for x in (os.getenv("NAICS_WHITELIST") or "").split(",") if x.strip()}
UEI = os.getenv("UEI")
CAGE_CODE = os.getenv("CAGE_CODE")
FPDS_ATOM_FEED = os.getenv("FPDS_ATOM_FEED")
SAM_SEARCH_API = os.getenv("SAM_SEARCH_API") or os.getenv("SAM_SEARCH_API", os.getenv("SAM_API"))

MAX_RETRIES = 5
BASE_BACKOFF_SECONDS = 1.0


def _jitter_delay(attempt: int) -> float:
    base = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
    return base + random.uniform(0, 0.5)


def _http_get(url: str, params: Dict[str, Any] | None = None, headers: Dict[str, str] | None = None) -> requests.Response:
    attempt = 0
    while True:
        attempt += 1
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=20)
            if resp.status_code == 403 or (500 <= resp.status_code < 600):
                if attempt >= MAX_RETRIES:
                    return resp
                time.sleep(_jitter_delay(attempt))
                continue
            if resp.status_code == 429:
                if attempt >= MAX_RETRIES:
                    return resp
                # throttle
                time.sleep(_jitter_delay(attempt) + 1)
                continue
            return resp
        except Exception:
            if attempt >= MAX_RETRIES:
                raise
            time.sleep(_jitter_delay(attempt))


def _filter_opps(opps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    now = datetime.datetime.utcnow()
    within = now + datetime.timedelta(days=7)
    filtered: List[Dict[str, Any]] = []
    for opp in opps:
        naics = str(opp.get("naicsCode") or opp.get("naics") or "").strip()
        if NAICS_WHITELIST and naics not in NAICS_WHITELIST:
            continue
        due_raw = opp.get("responseDate") or opp.get("closeDate") or opp.get("dueDate")
        try:
            if not due_raw:
                continue
            due = datetime.datetime.fromisoformat(str(due_raw).replace("Z", "+00:00"))
        except Exception:
            continue
        if not (now <= due <= within):
            continue
        t = (opp.get("type") or "").lower()
        title = (opp.get("title") or "").lower()
        is_combined = "combined" in t or "synopsis" in t or "solicitation" in t or "combined synopsis" in title
        if not is_combined:
            continue
        filtered.append(opp)
    return filtered


def _build_bid_pack(opp: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": opp.get("title"),
        "solicitationNumber": opp.get("solicitationNumber"),
        "naicsCode": opp.get("naicsCode"),
        "dueDate": opp.get("responseDate") or opp.get("closeDate") or opp.get("dueDate"),
        "agency": opp.get("agency"),
        "contact": (opp.get("officers") or [{}])[0],
        "links": {
            "ui": opp.get("uiLink") or opp.get("link"),
            "attachments": opp.get("attachments", []),
        },
        "meta": {
            "uei": UEI,
            "cage": CAGE_CODE,
        },
    }


def pull_sam() -> List[Dict[str, Any]]:
    if not SAM_SEARCH_API:
        return []
    params = {
        "limit": 50,
        "sort": "-publishDate",
        "postedFrom": (datetime.date.today() - datetime.timedelta(days=14)).isoformat(),
        "postedTo": datetime.date.today().isoformat(),
    }
    r = _http_get(SAM_SEARCH_API, params=params)
    if r.status_code != 200:
        post_err(f"SAM.gov HTTP {r.status_code}")
        return []
    try:
        data = r.json().get("opportunitiesData", [])
        return data
    except Exception as e:  # noqa: BLE001
        post_err(f"SAM.gov parse error: {e}")
        return []


def pull_fpds() -> List[Dict[str, Any]]:
    if not FPDS_ATOM_FEED:
        return []
    r = _http_get(FPDS_ATOM_FEED)
    if r.status_code != 200:
        return []
    # Minimal parse to structure similar to SAM entries
    try:
        import xml.etree.ElementTree as ET

        root = ET.fromstring(r.text)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        items: List[Dict[str, Any]] = []
        for entry in root.findall("a:entry", ns)[:50]:
            title = entry.findtext("a:title", namespaces=ns) or ""
            link_el = entry.find("a:link", ns)
            link = link_el.get("href") if link_el is not None else ""
            updated = entry.findtext("a:updated", namespaces=ns) or ""
            items.append({
                "title": title,
                "uiLink": link,
                "responseDate": updated,
                "type": "combined synopsis/solicitation",
                "solicitationNumber": title.split()[0] if title else "",
                "naicsCode": "",
            })
        return items
    except Exception:
        return []


def run_govcon() -> int:
    sam = pull_sam()
    fpds = pull_fpds()
    candidates = _filter_opps(sam + fpds)

    # Dedupe by solicitation number
    existing = fetch_all("GovCon_Opportunities")
    existing_ids = {r["fields"].get("Solicitation #") for r in existing}

    added = 0
    for d in candidates:
        sid = d.get("solicitationNumber")
        if not sid or sid in existing_ids:
            continue
        officer = (d.get("officers") or [{}])[0]
        email = officer.get("email", "")
        if not email:
            continue
        bid_pack = _build_bid_pack(d)
        record = {
            "Solicitation #": sid,
            "Title": d.get("title", ""),
            "NAICS": d.get("naicsCode", ""),
            "Due_Date": d.get("responseDate", ""),
            "Officer": officer.get("fullName", ""),
            "Email": email,
            "Status": d.get("type", ""),
            "Link": d.get("uiLink", ""),
            "bid_pack": bid_pack,
            "Timestamp": datetime.datetime.utcnow().isoformat(),
            # Dedupe key
            "source_id": sid,
        }
        safe_airtable_write("GovCon_Opportunities", record, key_fields=["source_id"])  # idempotent
        added += 1
    post_ops(f"GovCon loop added {added} opportunities")
    return added


"""GOVCON_SUBTRAP_ENGINE — FPDS atom + SAM JSON → GovCon Opportunities"""
import os
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

from src.common import AirtableClient, notify_ops, log_crack, get_json_retry, get_text_retry

SAM_SEARCH_API = os.getenv("SAM_SEARCH_API", "")
FPDS_ATOM_FEED = os.getenv("FPDS_ATOM_FEED", "")
NAICS_WHITELIST = os.getenv("NAICS_WHITELIST", "").split(",") if os.getenv("NAICS_WHITELIST") else []
RUN_INTERVAL_MINUTES = int(os.getenv("RUN_INTERVAL_MINUTES", "60"))


def fetch_sam() -> List[Dict[str, Any]]:
    """Fetch opportunities from SAM.gov API (optional)"""
    if not SAM_SEARCH_API.strip():
        return []
    
    status, data = get_json_retry(SAM_SEARCH_API)
    if status != 200:
        raise RuntimeError(f"SAM HTTP {status}: {str(data)[:500]}")
    
    # Handle various SAM response formats
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ["opportunitiesData", "notices", "results", "data"]:
            if key in data and isinstance(data[key], list):
                return data[key]
    return []


def fetch_fpds() -> List[Dict[str, Any]]:
    """Fetch awards from FPDS atom feed"""
    if not FPDS_ATOM_FEED.strip():
        return []
    
    status, text = get_text_retry(FPDS_ATOM_FEED)
    if status != 200:
        raise RuntimeError(f"FPDS HTTP {status}: {text[:500]}")
    
    root = ET.fromstring(text)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    entries = root.findall("a:entry", ns)

    out = []
    for e in entries:
        title = (e.findtext("a:title", default="", namespaces=ns) or "").strip()
        link = ""
        link_el = e.find("a:link", ns)
        if link_el is not None:
            link = link_el.attrib.get("href", "")
        updated = (e.findtext("a:updated", default="", namespaces=ns) or "").strip()
        summary = (e.findtext("a:summary", default="", namespaces=ns) or "").strip()
        
        out.append({
            "Title": title,
            "URL": link,
            "Updated": updated,
            "Source": "FPDS",
            "Raw": (title + " " + summary)[:10000]
        })
    return out


def normalize_sam(rec: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize SAM record to standard fields"""
    return {
        "Title": rec.get("title") or "Untitled",
        "Solicitation ID": rec.get("solicitationNumber") or rec.get("noticeId"),
        "Agency": rec.get("departmentName") or rec.get("agency"),
        "Due Date": rec.get("responseDeadLine"),
        "NAICS": rec.get("naicsCode"),
        "Set Aside": rec.get("setAsideCode"),
        "URL": rec.get("uiLink") or rec.get("link"),
        "Source": "SAM",
        "Raw": str(rec)[:10000],
    }


def filter_by_naics(opps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter opportunities by NAICS whitelist"""
    if not NAICS_WHITELIST:
        return opps
    
    filtered = []
    for opp in opps:
        naics = opp.get("NAICS") or ""
        if not naics:
            filtered.append(opp)  # Include if no NAICS
            continue
        
        if any(naics.startswith(allowed) for allowed in NAICS_WHITELIST):
            filtered.append(opp)
    
    return filtered


def run_govcon_engine(client: AirtableClient):
    """Main engine execution"""
    print(f"[GOVCON] Starting run at {datetime.now().isoformat()}")
    
    # Fetch from both sources
    sam_recs = fetch_sam()
    fpds_recs = fetch_fpds()
    
    print(f"[GOVCON] Fetched SAM: {len(sam_recs)}, FPDS: {len(fpds_recs)}")

    created = 0
    updated = 0
    opp_table = "GovCon Opportunities"

    # Process SAM records
    for r in sam_recs:
        norm = normalize_sam(r)
        filtered = filter_by_naics([norm])
        if not filtered:
            continue
        
        res = client.safe_upsert(
            opp_table,
            norm,
            match_fields=["Solicitation ID", "URL", "Title"],
            typecast=False,
        )
        created += 1 if res["action"] == "created" else 0
        updated += 1 if res["action"] == "updated" else 0

    # Process FPDS records
    fpds_filtered = filter_by_naics(fpds_recs)
    for r in fpds_filtered:
        res = client.safe_upsert(
            opp_table,
            r,
            match_fields=["URL", "Title"],
            typecast=False,
        )
        created += 1 if res["action"] == "created" else 0
        updated += 1 if res["action"] == "updated" else 0

    return {
        "sam_fetched": len(sam_recs),
        "fpds_fetched": len(fpds_recs),
        "fpds_filtered": len(fpds_filtered),
        "created": created,
        "updated": updated,
    }


def main():
    """Main service loop"""
    print(f"[GOVCON] Starting service at {datetime.now().isoformat()}")
    print(f"[GOVCON] Run interval: {RUN_INTERVAL_MINUTES} minutes")
    print(f"[GOVCON] SAM: {'ENABLED' if SAM_SEARCH_API else 'DISABLED'}")
    print(f"[GOVCON] FPDS: {'ENABLED' if FPDS_ATOM_FEED else 'DISABLED'}")
    
    try:
        client = AirtableClient()
    except Exception as e:
        print(f"[GOVCON] FATAL: Airtable init failed: {e}")
        return
    
    notify_ops("✅ GOVCON_SUBTRAP_ENGINE online")

    while True:
        start = time.time()
        try:
            stats = run_govcon_engine(client)
            client.log_kpi("govcon_run", stats)
            print(f"[GOVCON] {stats}")
            notify_ops(f"📋 GovCon: +{stats['created']} new | ~{stats['updated']} updated")
        except Exception as e:
            print(f"[GOVCON] ERROR: {e}")
            log_crack("govcon_engine", str(e), client)

        elapsed = time.time() - start
        sleep_time = max(5, RUN_INTERVAL_MINUTES * 60 - int(elapsed))
        print(f"[GOVCON] Next run in {sleep_time}s")
        time.sleep(sleep_time)


if __name__ == "__main__":
    main()

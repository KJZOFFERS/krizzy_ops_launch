# src/govcon_subtrap_engine.py

"""GOVCON_SUBTRAP_ENGINE — FPDS atom + SAM JSON → GovCon Opportunities"""
import os
import time
from datetime import datetime
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

from src.common import AirtableClient, get_text_retry
from src.ops import send_ops, send_crack, guard_engine
from src.utils import fetch_sam_opportunities

FPDS_ATOM_FEED = os.getenv("FPDS_ATOM_FEED", "")
NAICS_WHITELIST = os.getenv("NAICS_WHITELIST", "").split(",") if os.getenv("NAICS_WHITELIST") else []
RUN_INTERVAL_MINUTES = int(os.getenv("RUN_INTERVAL_MINUTES", "15"))


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
            filtered.append(opp)
            continue
        
        if any(naics.startswith(allowed) for allowed in NAICS_WHITELIST):
            filtered.append(opp)
    
    return filtered


@guard_engine("govcon_engine", max_consecutive_failures=5, disable_seconds=600)
def run_govcon_cycle(client: AirtableClient) -> Dict[str, Any]:
    """Main engine execution - one cycle"""
    print(f"[GOVCON] Starting run at {datetime.now().isoformat()}")
    
    # Fetch from both sources
    sam_recs = []
    sam_meta = {"status": 0}
    
    try:
        sam_recs, sam_meta = fetch_sam_opportunities()
        if sam_meta["status"] != 200 and sam_meta["status"] != 0:
            send_crack(
                "govcon_engine",
                f"SAM API error: {sam_meta['detail']}",
                {"status": sam_meta["status"]}
            )
    except Exception as e:
        send_crack("govcon_engine", f"SAM fetch exception: {e}")
    
    fpds_recs = []
    try:
        fpds_recs = fetch_fpds()
    except Exception as e:
        send_crack("govcon_engine", f"FPDS fetch failed: {e}")
    
    print(f"[GOVCON] Fetched SAM: {len(sam_recs)}, FPDS: {len(fpds_recs)}")

    created = 0
    updated = 0
    opp_table = "GovCon Opportunities"

    # Process SAM records
    for r in sam_recs:
        try:
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
        except Exception as e:
            send_crack("govcon_engine", f"SAM record upsert failed: {e}")

    # Process FPDS records
    fpds_filtered = filter_by_naics(fpds_recs)
    for r in fpds_filtered:
        try:
            res = client.safe_upsert(
                opp_table,
                r,
                match_fields=["URL", "Title"],
                typecast=False,
            )
            created += 1 if res["action"] == "created" else 0
            updated += 1 if res["action"] == "updated" else 0
        except Exception as e:
            send_crack("govcon_engine", f"FPDS record upsert failed: {e}")

    return {
        "sam_fetched": len(sam_recs),
        "sam_status": sam_meta["status"],
        "fpds_fetched": len(fpds_recs),
        "fpds_filtered": len(fpds_filtered),
        "created": created,
        "updated": updated,
    }


def main():
    """Main service loop"""
    print(f"[GOVCON] Starting service at {datetime.now().isoformat()}")
    print(f"[GOVCON] Run interval: {RUN_INTERVAL_MINUTES} minutes")
    print(f"[GOVCON] SAM: {'ENABLED' if os.getenv('SAM_SEARCH_API') else 'DISABLED'}")
    print(f"[GOVCON] FPDS: {'ENABLED' if FPDS_ATOM_FEED else 'DISABLED'}")
    
    try:
        client = AirtableClient()
    except Exception as e:
        print(f"[GOVCON] FATAL: Airtable init failed: {e}")
        send_crack("govcon_engine", f"Airtable init failed: {e}")
        return
    
    send_ops("✅ GOVCON_SUBTRAP_ENGINE online")

    while True:
        start = time.time()
        
        stats = run_govcon_cycle(client)
        
        if stats:
            client.log_kpi("govcon_run", stats)
            print(f"[GOVCON] {stats}")
            send_ops(f"📋 GovCon: +{stats['created']} new | ~{stats['updated']} updated")

        elapsed = time.time() - start
        sleep_time = max(5, RUN_INTERVAL_MINUTES * 60 - int(elapsed))
        print(f"[GOVCON] Next run in {sleep_time}s")
        time.sleep(sleep_time)


if __name__ == "__main__":
    main()

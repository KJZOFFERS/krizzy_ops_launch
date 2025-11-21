import os
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

from common import AirtableClient, notify_ops, log_crack, get_json_retry, get_text_retry

SAM_SEARCH_API = os.getenv("SAM_SEARCH_API", "")
FPDS_ATOM_FEED = os.getenv("FPDS_ATOM_FEED", "")
RUN_INTERVAL_MINUTES = int(os.getenv("RUN_INTERVAL_MINUTES", "15"))


def fetch_sam() -> List[Dict[str, Any]]:
    if not SAM_SEARCH_API.strip():
        return []
    status, data = get_json_retry(SAM_SEARCH_API)
    if status != 200:
        raise RuntimeError(f"SAM HTTP {status}: {str(data)[:500]}")
    return data.get("opportunitiesData", []) or []


def fetch_fpds() -> List[Dict[str, Any]]:
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
        out.append({"Title": title, "URL": link, "Updated": updated, "Source": "fpds", "Raw": title[:10000]})
    return out


def normalize_sam(rec: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "Title": rec.get("title"),
        "Solicitation ID": rec.get("solicitationNumber") or rec.get("noticeId"),
        "Agency": rec.get("departmentName") or rec.get("agency"),
        "Due Date": rec.get("responseDeadLine"),
        "NAICS": rec.get("naicsCode"),
        "Set Aside": rec.get("setAsideCode"),
        "URL": rec.get("uiLink") or rec.get("link"),
        "Source": "sam",
        "Raw": str(rec)[:10000],
    }


def run_once(client: AirtableClient):
    sam_recs = fetch_sam()
    fpds_recs = fetch_fpds()

    created = 0
    updated = 0

    opp_table = "GovCon Opportunities"

    for r in sam_recs:
        p = normalize_sam(r)
        res = client.safe_upsert(
            opp_table,
            p,
            match_fields=["Solicitation ID", "URL", "Title"],
            typecast=False,
        )
        created += 1 if res["action"] == "created" else 0
        updated += 1 if res["action"] == "updated" else 0

    for r in fpds_recs:
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
        "created": created,
        "updated": updated,
    }


def main():
    client = AirtableClient()
    notify_ops("GOVCON_SUBTRAP_ENGINE online.")

    while True:
        start = time.time()
        try:
            stats = run_once(client)
            client.log_kpi("govcon_run", stats)
            notify_ops(f"GOVCON ok: {stats}")
        except Exception as e:
            log_crack("govcon_engine", str(e), client)

        elapsed = time.time() - start
        time.sleep(max(5, RUN_INTERVAL_MINUTES * 60 - int(elapsed)))


if __name__ == "__main__":
    main()

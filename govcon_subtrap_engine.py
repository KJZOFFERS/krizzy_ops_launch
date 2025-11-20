#!/usr/bin/env python3
"""
GOVCON SUBTRAP ENGINE (Schema-safe)
- Pulls SAM_SEARCH_API (JSON) + FPDS_ATOM_FEED (Atom/XML).
- Filters NAICS if whitelist set.
- Filters expired.
- Dedupes.
- Writes only to detected fields in GovCon_Opportunities.
"""

import os
import json
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import requests
import feedparser


# ------------------ Discord ------------------

def send_discord(message: str, level="INFO"):
    webhook = os.getenv("DISCORD_WEBHOOK_ERRORS") if level == "ERROR" else os.getenv("DISCORD_WEBHOOK_OPS")
    if not webhook:
        return
    payload = {
        "embeds": [{
            "title": f"🏛️ GOVCON_SUBTRAP | {level}",
            "description": message,
            "color": 15158332 if level == "ERROR" else 3066993,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }]
    }
    try:
        requests.post(webhook, json=payload, timeout=10)
    except Exception:
        pass


# ------------------ Airtable Core ------------------

def airtable_headers():
    return {
        "Authorization": f"Bearer {os.getenv('AIRTABLE_API_KEY')}",
        "Content-Type": "application/json"
    }

def airtable_base_url():
    return f"https://api.airtable.com/v0/{os.getenv('AIRTABLE_BASE_ID')}"

def airtable_meta_tables() -> List[Dict[str, Any]]:
    url = f"https://api.airtable.com/v0/meta/bases/{os.getenv('AIRTABLE_BASE_ID')}/tables"
    r = requests.get(url, headers=airtable_headers(), timeout=20)
    r.raise_for_status()
    return r.json().get("tables", [])

def get_table_schema(table_name: str) -> Dict[str, Dict[str, Any]]:
    try:
        tables = airtable_meta_tables()
        for t in tables:
            if t.get("name") == table_name:
                schema = {}
                for f in t.get("fields", []):
                    schema[f["name"]] = {
                        "type": f.get("type"),
                        "options": f.get("options", {})
                    }
                return schema
    except Exception as e:
        send_discord(f"Schema fetch failed for {table_name}: {e}", level="ERROR")
    return {}

def get_records(table_name: str, max_records=2000) -> List[Dict[str, Any]]:
    records = []
    url = f"{airtable_base_url()}/{table_name}"
    params = {"pageSize": 100}
    offset = None
    while True:
        if offset:
            params["offset"] = offset
        r = requests.get(url, headers=airtable_headers(), params=params, timeout=30)
        r.raise_for_status()
        j = r.json()
        records.extend(j.get("records", []))
        offset = j.get("offset")
        if not offset or len(records) >= max_records:
            break
    return records[:max_records]

def create_record(table_name: str, fields: Dict[str, Any]):
    url = f"{airtable_base_url()}/{table_name}"
    r = requests.post(url, headers=airtable_headers(), json={"fields": fields}, timeout=30)
    r.raise_for_status()
    return r.json()


# ------------------ Proxy Rotation ------------------

def get_proxies():
    pool = os.getenv("PROXY_ROTATE_POOL", "").strip()
    single = os.getenv("PROXY_HTTP", "").strip()
    if pool:
        proxies = [p.strip() for p in pool.split(",") if p.strip()]
        if proxies:
            p = random.choice(proxies)
            if not p.startswith("http"):
                p = "http://" + p
            return {"http": p, "https": p}
    if single:
        p = single if single.startswith("http") else ("http://" + single)
        return {"http": p, "https": p}
    return None


# ------------------ Field Detection ------------------

def detect_field(schema: Dict[str, Dict[str, Any]], patterns: List[str]) -> Optional[str]:
    if not schema:
        return None
    lower_map = {k.lower(): k for k in schema.keys()}
    for p in patterns:
        pl = p.lower()
        if pl in lower_map:
            return lower_map[pl]
        for k_low, k in lower_map.items():
            if pl in k_low:
                return k
    return None


# ------------------ Feed Fetching ------------------

def fetch_sam_opportunities() -> List[Dict[str, Any]]:
    url = os.getenv("SAM_SEARCH_API", "").strip()
    if not url:
        return []
    try:
        r = requests.get(url, params={"limit": 50, "ueiSAM": os.getenv("UEI", "").strip() or None},
                         proxies=get_proxies(), timeout=30)
        r.raise_for_status()
        data = r.json()

        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ["opportunitiesData", "notices", "results", "data"]:
                if key in data and isinstance(data[key], list):
                    return data[key]
        return []
    except requests.exceptions.RequestException as e:
        send_discord(f"SAM network error: {e}", level="ERROR")
        return []
    except json.JSONDecodeError as e:
        send_discord(f"SAM JSON parse error: {e}", level="ERROR")
        return []
    except Exception as e:
        send_discord(f"SAM unknown error: {e}", level="ERROR")
        return []

def fetch_fpds_opportunities() -> List[Dict[str, Any]]:
    url = os.getenv("FPDS_ATOM_FEED", "").strip()
    if not url:
        return []
    try:
        proxies = get_proxies()
        if proxies:
            r = requests.get(url, proxies=proxies, timeout=30)
            r.raise_for_status()
            feed = feedparser.parse(r.content)
        else:
            feed = feedparser.parse(url)

        if feed.bozo:
            send_discord(f"FPDS parse warning: {feed.bozo_exception}", level="ERROR")

        out = []
        for e in feed.entries[:50]:
            out.append({
                "title": e.get("title", ""),
                "description": e.get("summary", ""),
                "url": e.get("link", ""),
                "published": e.get("published", ""),
                "id": e.get("id", ""),
                "source": "FPDS"
            })
        return out
    except requests.exceptions.RequestException as e:
        send_discord(f"FPDS network error: {e}", level="ERROR")
        return []
    except Exception as e:
        send_discord(f"FPDS parse error: {e}", level="ERROR")
        return []


# ------------------ Filters ------------------

def filter_by_naics(opps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    wl = os.getenv("NAICS_WHITELIST", "").strip()
    if not wl:
        return opps
    allowed = [x.strip() for x in wl.split(",") if x.strip()]
    filtered = []
    for o in opps:
        naics = str(o.get("naicsCode") or o.get("naics") or o.get("classificationCode") or "")
        if not naics:
            filtered.append(o)
            continue
        if any(naics.startswith(a) for a in allowed):
            filtered.append(o)
    return filtered

def filter_expired(opps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    keep = []
    for o in opps:
        ds = o.get("responseDeadLine") or o.get("dueDate") or o.get("deadline") or o.get("published") or ""
        if not ds:
            keep.append(o)
            continue
        try:
            if "T" in ds:
                d = datetime.fromisoformat(ds.replace("Z", "+00:00"))
            else:
                d = datetime.strptime(ds, "%m/%d/%Y").replace(tzinfo=timezone.utc)
            if d > now:
                keep.append(o)
        except Exception:
            keep.append(o)
    return keep


# ------------------ Dedupe ------------------

def dedupe(opps: List[Dict[str, Any]], existing: List[Dict[str, Any]], schema) -> List[Dict[str, Any]]:
    existing_ids = set()

    id_field = detect_field(schema, ["notice id", "notice_id", "solicitation", "opportunity id", "id", "url", "link"])
    for r in existing:
        f = r.get("fields", {})
        if id_field and id_field in f:
            existing_ids.add(str(f[id_field]))
        for k, v in f.items():
            kl = k.lower()
            if any(x in kl for x in ["notice", "solicitation", "id", "url"]):
                existing_ids.add(str(v))

    out = []
    for o in opps:
        oid = str(o.get("noticeId") or o.get("solicitationNumber") or o.get("id") or o.get("url") or "")
        if oid and oid in existing_ids:
            continue
        out.append(o)
        if oid:
            existing_ids.add(oid)
    return out


# ------------------ Mapping ------------------

def map_to_schema(o: Dict[str, Any], schema) -> Dict[str, Any]:
    mapped = {}

    title_f = detect_field(schema, ["title", "name", "opportunity title"])
    desc_f = detect_field(schema, ["description", "summary", "details", "body"])
    url_f = detect_field(schema, ["url", "link"])
    id_f = detect_field(schema, ["notice id", "notice_id", "solicitation", "id"])
    naics_f = detect_field(schema, ["naics", "naics code"])
    due_f = detect_field(schema, ["deadline", "response deadline", "due date", "close date"])
    agency_f = detect_field(schema, ["agency", "department", "organization"])
    amount_f = detect_field(schema, ["amount", "value", "award", "estimated"])
    status_f = detect_field(schema, ["status"])
    posted_f = detect_field(schema, ["posted date", "published", "date posted"])
    captured_f = detect_field(schema, ["captured at", "ingested", "imported"])
    type_f = detect_field(schema, ["type", "notice type", "category"])

    if title_f:
        mapped[title_f] = o.get("title") or o.get("noticeId") or "Untitled"
    if desc_f:
        mapped[desc_f] = (o.get("description") or o.get("summary") or "")[:5000]
    if url_f:
        mapped[url_f] = o.get("url") or o.get("uiLink") or ""
    if id_f:
        mapped[id_f] = o.get("noticeId") or o.get("solicitationNumber") or o.get("id") or ""
    if naics_f:
        mapped[naics_f] = o.get("naicsCode") or o.get("naics") or ""
    if due_f:
        mapped[due_f] = o.get("responseDeadLine") or o.get("dueDate") or o.get("deadline") or ""
    if agency_f:
        mapped[agency_f] = o.get("department") or o.get("agency") or ""
    if amount_f:
        amt = o.get("award", {}).get("amount") if isinstance(o.get("award"), dict) else o.get("amount")
        mapped[amount_f] = amt or ""
    if status_f:
        mapped[status_f] = "New"
    if posted_f:
        mapped[posted_f] = o.get("postedDate") or o.get("published") or datetime.now(timezone.utc).isoformat()
    if captured_f:
        mapped[captured_f] = datetime.now(timezone.utc).isoformat()
    if type_f:
        mapped[type_f] = o.get("noticeType") or o.get("type") or o.get("source") or ""

    return {k: v for k, v in mapped.items() if v != ""}


# ------------------ Main Engine ------------------

def run_govcon_engine():
    if not os.getenv("AIRTABLE_API_KEY") or not os.getenv("AIRTABLE_BASE_ID"):
        return "❌ Missing Airtable creds"

    schema = get_table_schema("GovCon_Opportunities")
    if not schema:
        send_discord("GovCon blocked: cannot detect GovCon_Opportunities schema", level="ERROR")
        return "❌ GovCon blocked: no schema"

    sam = fetch_sam_opportunities()
    fpds = fetch_fpds_opportunities()
    all_opps = sam + fpds
    if not all_opps:
        return "✅ No opportunities from feeds"

    filtered = filter_expired(filter_by_naics(all_opps))

    try:
        existing = get_records("GovCon_Opportunities")
    except Exception:
        existing = []

    new_opps = dedupe(filtered, existing, schema)
    if not new_opps:
        return f"✅ No new opps (fetched {len(all_opps)}, filtered {len(filtered)})"

    created = 0
    errors = 0
    for o in new_opps[:20]:
        try:
            mapped = map_to_schema(o, schema)
            if not mapped:
                errors += 1
                continue
            create_record("GovCon_Opportunities", mapped)
            created += 1
        except Exception:
            errors += 1

    return f"Fetched {len(all_opps)} | Filtered {len(filtered)} | Created {created} | Errors {errors}"


if __name__ == "__main__":
    print(run_govcon_engine())

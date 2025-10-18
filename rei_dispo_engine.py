import requests, datetime
from airtable_utils import add_record, fetch_all
from discord_utils import post_ops, post_error

# Zillow & Craigslist scrapers use their public RSS/JSON feeds.
ZILLOW_SEARCH = "https://www.zillow.com/homes/for_sale/?format=json"
CRAIGSLIST_SEARCH = "https://www.craigslist.org/search/rea?format=rss"

def parse_zillow():
    try:
        data = requests.get(ZILLOW_SEARCH, timeout=10).json()
    except Exception as e:
        post_error(f"Zillow pull failed: {e}")
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

def parse_craigslist():
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
    except Exception as e:
        post_error(f"Craigslist parse failed: {e}")
    return leads

def deduplicate(new, existing):
    existing_urls = {r["fields"].get("Source_URL") for r in existing}
    return [x for x in new if x["Source_URL"] not in existing_urls]

def run_rei():
    z = parse_zillow()
    c = parse_craigslist()
    leads = z + c
    existing = fetch_all("Leads_REI")
    clean = [x for x in deduplicate(leads, existing) if x.get("Phone") or x.get("Email")]
    for l in clean:
        add_record("Leads_REI", l)
    post_ops(f"REI loop added {len(clean)} verified leads.")
    return len(clean)

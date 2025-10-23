import os
import requests
import datetime
import hashlib
import logging
from typing import List, Dict, Any, Optional
from airtable_utils import safe_airtable_write, fetch_all, create_dedup_key
from discord_utils import post_ops, post_error
from twilio_utils import send_msg, send_bulk_sms
from kpi import track_cycle_start, track_cycle_end, track_error
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Data sources
ZILLOW_SEARCH = "https://www.zillow.com/homes/for_sale/?format=json"
CRAIGSLIST_SEARCH = "https://www.craigslist.org/search/rea?format=rss"

# NAICS whitelist for filtering
NAICS_WHITELIST = os.getenv("NAICS_WHITELIST", "").split(",") if os.getenv("NAICS_WHITELIST") else []

class REIError(Exception):
    """Custom exception for REI operations"""
    pass

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type((requests.exceptions.RequestException, REIError))
)
def parse_zillow() -> List[Dict[str, Any]]:
    """Parse Zillow data with retry logic"""
    try:
        response = requests.get(ZILLOW_SEARCH, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        logger.error(f"Zillow pull failed: {e}")
        post_error(f"Zillow pull failed: {e}")
        raise REIError(f"Zillow data fetch failed: {e}")

    leads = []
    for item in data.get("props", [])[:20]:
        if not item.get("address") or not item.get("price"):
            continue
        
        # Create hash for phone/email deduplication
        phone_hash = hashlib.md5((item.get("brokerPhone", "") or "").lower().strip().encode()).hexdigest()
        email_hash = hashlib.md5((item.get("brokerEmail", "") or "").lower().strip().encode()).hexdigest()
        
        leads.append({
            "Address": item.get("address"),
            "City": item.get("city"),
            "State": item.get("state"),
            "Zip": item.get("zipcode"),
            "Price": item.get("price"),
            "ARV": item.get("price"),  # Using price as ARV placeholder
            "Agent": item.get("brokerName", ""),
            "Phone": item.get("brokerPhone", ""),
            "Email": item.get("brokerEmail", ""),
            "Phone_Hash": phone_hash,
            "Email_Hash": email_hash,
            "Source_URL": f"https://www.zillow.com{item.get('detailUrl','')}",
            "Source": "Zillow",
            "Timestamp": datetime.datetime.utcnow().isoformat(),
            "Status": "New"
        })
    
    logger.info(f"Parsed {len(leads)} Zillow leads")
    return leads

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type((requests.exceptions.RequestException, REIError))
)
def parse_craigslist() -> List[Dict[str, Any]]:
    """Parse Craigslist data with retry logic"""
    import xml.etree.ElementTree as ET
    
    leads = []
    try:
        response = requests.get(CRAIGSLIST_SEARCH, timeout=15)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        
        for item in root.findall(".//item")[:10]:
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            
            if not title or not link:
                continue
            
            leads.append({
                "Address": title,
                "City": "",
                "State": "",
                "Zip": "",
                "Price": "",
                "ARV": "",
                "Agent": "",
                "Phone": "",
                "Email": "",
                "Phone_Hash": "",
                "Email_Hash": "",
                "Source_URL": link,
                "Source": "Craigslist",
                "Timestamp": datetime.datetime.utcnow().isoformat(),
                "Status": "New"
            })
            
    except Exception as e:
        logger.error(f"Craigslist parse failed: {e}")
        post_error(f"Craigslist parse failed: {e}")
        raise REIError(f"Craigslist data fetch failed: {e}")
    
    logger.info(f"Parsed {len(leads)} Craigslist leads")
    return leads

def deduplicate_leads(new_leads: List[Dict[str, Any]], existing_leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate leads based on source_id and phone/email hash"""
    existing_keys = set()
    
    for record in existing_leads:
        fields = record.get("fields", {})
        source_id = fields.get("Source_URL", "")
        phone_hash = fields.get("Phone_Hash", "")
        email_hash = fields.get("Email_Hash", "")
        
        # Create dedup key
        dedup_key = f"{source_id}|{phone_hash}|{email_hash}"
        existing_keys.add(dedup_key)
    
    deduplicated = []
    for lead in new_leads:
        source_id = lead.get("Source_URL", "")
        phone_hash = lead.get("Phone_Hash", "")
        email_hash = lead.get("Email_Hash", "")
        
        dedup_key = f"{source_id}|{phone_hash}|{email_hash}"
        if dedup_key not in existing_keys:
            deduplicated.append(lead)
            existing_keys.add(dedup_key)  # Prevent duplicates within new batch
    
    logger.info(f"Deduplicated {len(new_leads)} leads to {len(deduplicated)} unique leads")
    return deduplicated

def send_lead_notifications(leads: List[Dict[str, Any]]) -> None:
    """Send SMS notifications for new leads"""
    if not leads:
        return
    
    # Get phone numbers from leads (you'd typically get these from a buyer list)
    # For now, we'll just log the notification
    logger.info(f"Would send notifications for {len(leads)} new leads")
    
    # Example notification logic:
    # buyer_phones = get_buyer_phone_numbers()  # Implement this based on your buyer data
    # for lead in leads:
    #     message = f"New REI lead: {lead['Address']} - ${lead['Price']} | Contact: {lead['Phone'] or lead['Email']}"
    #     send_bulk_sms(buyer_phones, message)

def run_rei() -> int:
    """Main REI engine execution"""
    try:
        track_cycle_start("REI")
        
        # Parse data from sources
        zillow_leads = parse_zillow()
        craigslist_leads = parse_craigslist()
        all_leads = zillow_leads + craigslist_leads
        
        # Get existing leads for deduplication
        existing_records = fetch_all("Leads_REI")
        
        # Deduplicate leads
        unique_leads = deduplicate_leads(all_leads, existing_records)
        
        # Filter leads with contact information
        verified_leads = [lead for lead in unique_leads if lead.get("Phone") or lead.get("Email")]
        
        # Write to Airtable with deduplication
        written_count = 0
        for lead in verified_leads:
            try:
                # Use source_id and phone/email hash for deduplication
                key_fields = ["Source_URL", "Phone_Hash", "Email_Hash"]
                safe_airtable_write("Leads_REI", lead, key_fields)
                written_count += 1
            except Exception as e:
                logger.error(f"Failed to write lead {lead.get('Address', 'Unknown')}: {e}")
                track_error("REI", f"Failed to write lead: {e}")
        
        # Send notifications
        send_lead_notifications(verified_leads)
        
        track_cycle_end("REI", written_count, success=True)
        post_ops(f"REI loop added {written_count} verified leads from {len(all_leads)} total")
        
        logger.info(f"REI cycle completed: {written_count} leads written")
        return written_count
        
    except Exception as e:
        track_error("REI", str(e))
        post_error(f"REI loop failed: {e}")
        logger.error(f"REI cycle failed: {e}")
        return 0

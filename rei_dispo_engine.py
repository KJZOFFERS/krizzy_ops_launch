import hashlib
import logging
from datetime import datetime
from typing import Any

import backoff
import feedparser
import requests

from airtable_utils import fetch_all, kpi_push, safe_airtable_write
from discord_utils import post_error, post_ops
from twilio_utils import format_phone_number, send_rei_message, validate_phone_number

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Data sources - using public APIs and RSS feeds
ZILLOW_RSS = "https://www.zillow.com/homes/for_sale/fsbo_lt/house_type/?searchQueryState=%7B%22pagination%22%3A%7B%7D%2C%22usersSearchTerm%22%3A%22FSBO%22%2C%22mapBounds%22%3A%7B%22west%22%3A-74.25909423828125%2C%22east%22%3A-73.70018005371094%2C%22south%22%3A40.477399%2C%22north%22%3A40.917577%7D%2C%22regionSelection%22%3A%5B%7B%22regionId%22%3A6181%2C%22regionType%22%3A3%7D%5D%2C%22isMapVisible%22%3Atrue%2C%22filterState%22%3A%7B%22fsbo%22%3A%7B%22value%22%3Atrue%7D%2C%22ah%22%3A%7B%22value%22%3Atrue%7D%7D%2C%22isListVisible%22%3Atrue%7D"
CRAIGSLIST_RSS = "https://newyork.craigslist.org/search/reo?format=rss"

# Additional sources for better coverage
REALTOR_COM_RSS = "https://www.realtor.com/rss/listings"
FSBO_COM_RSS = "https://www.fsbo.com/rss/listings"


@backoff.on_exception(
    backoff.expo, (requests.exceptions.RequestException,), max_tries=3, jitter=backoff.random_jitter
)
def fetch_rss_feed(url: str, source_name: str) -> list[dict[str, Any]]:
    """Fetch and parse RSS feed with error handling."""
    try:
        logger.info(f"Fetching {source_name} RSS feed")
        response = requests.get(
            url, timeout=15, headers={'User-Agent': 'Mozilla/5.0 (compatible; REI-Bot/1.0)'}
        )
        response.raise_for_status()

        feed = feedparser.parse(response.content)

        if feed.bozo:
            logger.warning(f"{source_name} RSS feed has parsing issues")

        return feed.entries[:50]  # Limit to 50 entries per source

    except Exception as e:
        logger.error(f"Failed to fetch {source_name} RSS: {e}")
        post_error(f"{source_name} RSS fetch failed: {str(e)}")
        return []


def parse_zillow_rss() -> list[dict[str, Any]]:
    """Parse Zillow RSS feed for FSBO listings."""
    entries = fetch_rss_feed(ZILLOW_RSS, "Zillow")
    leads = []

    for entry in entries:
        try:
            # Extract data from RSS entry
            title = getattr(entry, 'title', '')
            link = getattr(entry, 'link', '')
            description = getattr(entry, 'description', '')

            # Parse price from title or description
            import re

            price_match = re.search(r'\$([0-9,]+)', f"{title} {description}")
            price = price_match.group(1) if price_match else ""

            # Extract location info
            location_match = re.search(r'([^,]+),\s*([A-Z]{2})\s*(\d{5})', f"{title} {description}")
            city = location_match.group(1) if location_match else ""
            state = location_match.group(2) if location_match else ""
            zip_code = location_match.group(3) if location_match else ""

            leads.append(
                {
                    "Address": title.split(" - ")[0] if " - " in title else title,
                    "City": city,
                    "State": state,
                    "Zip": zip_code,
                    "Price": price,
                    "ARV": str(int(price.replace(",", "")) * 1.1)
                    if price and price.replace(",", "").isdigit()
                    else "",
                    "Agent": "FSBO",
                    "Phone": "",  # Will be enriched later
                    "Email": "",  # Will be enriched later
                    "Source": "Zillow_RSS",
                    "Source_URL": link,
                    "Description": description[:500],
                    "Timestamp": datetime.utcnow().isoformat(),
                }
            )

        except Exception as e:
            logger.warning(f"Error parsing Zillow entry: {e}")
            continue

    logger.info(f"Parsed {len(leads)} leads from Zillow RSS")
    return leads


def parse_craigslist_rss() -> list[dict[str, Any]]:
    """Parse Craigslist RSS feed for real estate listings."""
    entries = fetch_rss_feed(CRAIGSLIST_RSS, "Craigslist")
    leads = []

    for entry in entries:
        try:
            title = getattr(entry, 'title', '')
            link = getattr(entry, 'link', '')
            description = getattr(entry, 'description', '')

            # Extract price
            import re

            price_match = re.search(r'\$([0-9,]+)', f"{title} {description}")
            price = price_match.group(1) if price_match else ""

            # Extract phone from description
            phone_match = re.search(r'(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})', description)
            phone = phone_match.group(1) if phone_match else ""

            # Extract email
            email_match = re.search(
                r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', description
            )
            email = email_match.group(1) if email_match else ""

            leads.append(
                {
                    "Address": title,
                    "City": "",
                    "State": "",
                    "Zip": "",
                    "Price": price,
                    "ARV": str(int(price.replace(",", "")) * 0.7)
                    if price and price.replace(",", "").isdigit()
                    else "",
                    "Agent": "Private",
                    "Phone": phone,
                    "Email": email,
                    "Source": "Craigslist_RSS",
                    "Source_URL": link,
                    "Description": description[:500],
                    "Timestamp": datetime.utcnow().isoformat(),
                }
            )

        except Exception as e:
            logger.warning(f"Error parsing Craigslist entry: {e}")
            continue

    logger.info(f"Parsed {len(leads)} leads from Craigslist RSS")
    return leads


def parse_additional_sources() -> list[dict[str, Any]]:
    """Parse additional real estate sources."""
    all_leads = []

    # Realtor.com RSS
    realtor_entries = fetch_rss_feed(REALTOR_COM_RSS, "Realtor.com")
    for entry in realtor_entries[:25]:  # Limit per source
        try:
            title = getattr(entry, 'title', '')
            link = getattr(entry, 'link', '')

            all_leads.append(
                {
                    "Address": title,
                    "City": "",
                    "State": "",
                    "Zip": "",
                    "Price": "",
                    "ARV": "",
                    "Agent": "Realtor.com",
                    "Phone": "",
                    "Email": "",
                    "Source": "Realtor_RSS",
                    "Source_URL": link,
                    "Description": getattr(entry, 'description', '')[:500],
                    "Timestamp": datetime.utcnow().isoformat(),
                }
            )
        except Exception as e:
            logger.warning(f"Error parsing Realtor.com entry: {e}")
            continue

    logger.info(f"Parsed {len(all_leads)} additional leads")
    return all_leads


def enrich_lead_data(lead: dict[str, Any]) -> dict[str, Any]:
    """Enrich lead data with additional information."""
    # Format phone number if present
    if lead.get("Phone"):
        formatted_phone = format_phone_number(lead["Phone"])
        if formatted_phone:
            lead["Phone"] = formatted_phone
        else:
            lead["Phone"] = ""  # Invalid phone

    # Validate email format
    if lead.get("Email"):
        import re

        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, lead["Email"]):
            lead["Email"] = ""  # Invalid email

    # Calculate estimated ARV if not present
    if not lead.get("ARV") and lead.get("Price"):
        try:
            price_num = int(lead["Price"].replace(",", "").replace("$", ""))
            # Simple ARV calculation (price * 1.1 for appreciation)
            lead["ARV"] = str(int(price_num * 1.1))
        except (ValueError, AttributeError):
            pass

    # Add lead scoring
    score = 0
    if lead.get("Phone"):
        score += 30
    if lead.get("Email"):
        score += 20
    if lead.get("Price"):
        score += 25
    if lead.get("Address"):
        score += 25

    lead["Lead_Score"] = score

    return lead


def create_dedup_key(lead: dict[str, Any]) -> str:
    """Create deduplication key from lead data."""
    # Use source URL as primary key
    if lead.get("Source_URL"):
        return hashlib.sha256(lead["Source_URL"].encode()).hexdigest()[:16]

    # Fallback to address + phone/email hash
    key_parts = []
    if lead.get("Address"):
        key_parts.append(lead["Address"].lower().strip())

    contact = lead.get("Phone") or lead.get("Email") or ""
    if contact:
        key_parts.append(hashlib.sha256(contact.encode()).hexdigest()[:8])

    return hashlib.sha256("|".join(key_parts).encode()).hexdigest()[:16]


def send_outbound_messages(leads: list[dict[str, Any]]) -> int:
    """Send outbound messages to qualified leads."""
    sent_count = 0

    for lead in leads:
        # Only send to high-scoring leads with valid contact info
        if lead.get("Lead_Score", 0) < 50:
            continue

        phone = lead.get("Phone")
        if phone and validate_phone_number(phone):
            try:
                message_sid = send_rei_message(phone)
                if message_sid:
                    # Update lead with message info
                    lead["Message_Sent"] = True
                    lead["Message_SID"] = message_sid
                    lead["Message_Timestamp"] = datetime.utcnow().isoformat()
                    sent_count += 1

                    # Rate limiting - space out messages
                    import time

                    time.sleep(2)  # 2 second delay between messages

            except Exception as e:
                logger.warning(f"Failed to send message to {phone[:6]}*****: {e}")

    logger.info(f"Sent outbound messages to {sent_count} leads")
    return sent_count


def run_rei() -> int:
    """
    Run REI disposition engine with comprehensive lead processing.

    Returns:
        Number of new leads processed
    """
    logger.info("Starting REI disposition engine")

    try:
        # Fetch leads from all sources
        all_leads = []
        all_leads.extend(parse_zillow_rss())
        all_leads.extend(parse_craigslist_rss())
        all_leads.extend(parse_additional_sources())

        logger.info(f"Fetched {len(all_leads)} total leads from all sources")

        # Enrich lead data
        enriched_leads = []
        for lead in all_leads:
            try:
                enriched_lead = enrich_lead_data(lead)
                enriched_leads.append(enriched_lead)
            except Exception as e:
                logger.warning(f"Error enriching lead: {e}")
                continue

        # Filter for quality leads (must have contact info)
        quality_leads = [
            lead
            for lead in enriched_leads
            if (lead.get("Phone") or lead.get("Email")) and lead.get("Address")
        ]

        logger.info(f"Filtered to {len(quality_leads)} quality leads")

        # Deduplicate against existing records
        existing_records = fetch_all("Leads_REI")
        existing_dedup_keys = {
            r["fields"].get("dedup_key") for r in existing_records if r["fields"].get("dedup_key")
        }

        new_leads = []
        for lead in quality_leads:
            dedup_key = create_dedup_key(lead)
            if dedup_key not in existing_dedup_keys:
                lead["dedup_key"] = dedup_key
                new_leads.append(lead)

        logger.info(f"Found {len(new_leads)} new leads after deduplication")

        # Write new leads to Airtable
        written_count = 0
        for lead in new_leads:
            try:
                result = safe_airtable_write("Leads_REI", lead, ["dedup_key"])
                if result:
                    written_count += 1
            except Exception as e:
                logger.error(f"Error writing lead to Airtable: {e}")
                continue

        # Send outbound messages to qualified leads
        if written_count > 0:
            message_count = send_outbound_messages(new_leads)
            kpi_push("rei_messages", {"sent": message_count, "leads": written_count})

        # Log results
        post_ops(
            f"REI engine completed: {written_count} new leads, {len(all_leads)} total processed"
        )
        logger.info(f"REI engine completed: {written_count} new leads written")

        return written_count

    except Exception as e:
        logger.error(f"REI engine failed: {e}")
        post_error(f"REI engine failed: {str(e)}")
        return 0

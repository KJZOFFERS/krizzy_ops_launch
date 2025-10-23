import hashlib
import logging
import os
from datetime import date, datetime, timedelta
from typing import Any

import backoff
import feedparser
import requests

from airtable_utils import fetch_all, kpi_push, safe_airtable_write
from discord_utils import post_error, post_ops
from twilio_utils import format_phone_number, send_govcon_message

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables with exact names as specified
UEI = os.getenv("UEI")
CAGE_CODE = os.getenv("CAGE_CODE")
NAICS_WHITELIST = (
    os.getenv("NAICS_WHITELIST", "").split(",") if os.getenv("NAICS_WHITELIST") else []
)
FPDS_ATOM_FEED = os.getenv(
    "FPDS_ATOM_FEED",
    "https://www.fpds.gov/ezsearch/FEEDS/ATOM?FEEDNAME=PUBLIC&q=ACTIVE_DATE:[NOW-7DAYS+TO+NOW]",
)
SAM_SEARCH_API = os.getenv("SAM_SEARCH_API", "https://api.sam.gov/opportunities/v2/search")

# Clean up NAICS whitelist
NAICS_WHITELIST = [naics.strip() for naics in NAICS_WHITELIST if naics.strip()]

if not NAICS_WHITELIST:
    logger.warning("NAICS_WHITELIST not configured - will process all NAICS codes")

logger.info(f"Configured with {len(NAICS_WHITELIST)} whitelisted NAICS codes")


@backoff.on_exception(
    backoff.expo, (requests.exceptions.RequestException,), max_tries=3, jitter=backoff.random_jitter
)
def fetch_sam_opportunities() -> list[dict[str, Any]]:
    """Fetch opportunities from SAM.gov API."""
    try:
        # Calculate date range (last 7 days)
        end_date = date.today()
        start_date = end_date - timedelta(days=7)

        params = {
            "limit": 100,
            "offset": 0,
            "postedFrom": start_date.strftime("%m/%d/%Y"),
            "postedTo": end_date.strftime("%m/%d/%Y"),
            "ptype": "o",  # Opportunities only
            "sortBy": "-modifiedDate",
        }

        headers = {"User-Agent": "KRIZZY-OPS-GovCon/1.0", "Accept": "application/json"}

        logger.info(f"Fetching SAM opportunities from {start_date} to {end_date}")
        response = requests.get(SAM_SEARCH_API, params=params, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()
        opportunities = data.get("opportunitiesData", [])

        logger.info(f"Fetched {len(opportunities)} opportunities from SAM.gov")
        return opportunities

    except Exception as e:
        logger.error(f"Failed to fetch SAM opportunities: {e}")
        post_error(f"SAM.gov API fetch failed: {str(e)}")
        return []


@backoff.on_exception(
    backoff.expo, (requests.exceptions.RequestException,), max_tries=3, jitter=backoff.random_jitter
)
def fetch_fpds_feed() -> list[dict[str, Any]]:
    """Fetch opportunities from FPDS ATOM feed."""
    try:
        logger.info("Fetching FPDS ATOM feed")
        response = requests.get(
            FPDS_ATOM_FEED, timeout=30, headers={"User-Agent": "KRIZZY-OPS-GovCon/1.0"}
        )
        response.raise_for_status()

        feed = feedparser.parse(response.content)

        if feed.bozo:
            logger.warning("FPDS ATOM feed has parsing issues")

        opportunities = []
        for entry in feed.entries[:50]:  # Limit to 50 entries
            try:
                # Extract opportunity data from FPDS entry
                opportunity = {
                    "title": getattr(entry, "title", ""),
                    "link": getattr(entry, "link", ""),
                    "description": getattr(entry, "description", ""),
                    "published": getattr(entry, "published", ""),
                    "id": getattr(entry, "id", ""),
                    "source": "FPDS",
                }
                opportunities.append(opportunity)
            except Exception as e:
                logger.warning(f"Error parsing FPDS entry: {e}")
                continue

        logger.info(f"Fetched {len(opportunities)} opportunities from FPDS")
        return opportunities

    except Exception as e:
        logger.error(f"Failed to fetch FPDS feed: {e}")
        post_error(f"FPDS feed fetch failed: {str(e)}")
        return []


def filter_combined_synopsis_solicitation(
    opportunities: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Filter for Combined Synopsis/Solicitation opportunities."""
    filtered = []

    for opp in opportunities:
        title = opp.get("title", "").lower()
        description = opp.get("description", "").lower()
        opp_type = opp.get("type", "").lower()

        # Look for Combined Synopsis/Solicitation indicators
        combined_indicators = [
            "combined synopsis",
            "combined solicitation",
            "synopsis/solicitation",
            "full and open competition",
            "presolicitation",
            "sources sought",
        ]

        is_combined = any(
            indicator in f"{title} {description} {opp_type}" for indicator in combined_indicators
        )

        if is_combined:
            opp["opportunity_type"] = "Combined Synopsis/Solicitation"
            filtered.append(opp)

    logger.info(f"Filtered to {len(filtered)} Combined Synopsis/Solicitation opportunities")
    return filtered


def filter_by_due_date(opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter opportunities with due dates within 7 days."""
    filtered = []
    cutoff_date = datetime.utcnow() + timedelta(days=7)

    for opp in opportunities:
        due_date_str = opp.get("responseDate") or opp.get("dueDate") or ""

        if not due_date_str:
            continue

        try:
            # Parse various date formats
            due_date = None
            for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%d-%b-%Y"]:
                try:
                    due_date = datetime.strptime(due_date_str[:19], fmt)
                    break
                except ValueError:
                    continue

            if due_date and due_date <= cutoff_date:
                opp["parsed_due_date"] = due_date.isoformat()
                filtered.append(opp)

        except Exception as e:
            logger.warning(f"Error parsing due date '{due_date_str}': {e}")
            continue

    logger.info(f"Filtered to {len(filtered)} opportunities with due dates within 7 days")
    return filtered


def filter_by_naics(opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter opportunities by NAICS whitelist."""
    if not NAICS_WHITELIST:
        logger.info("No NAICS whitelist configured - accepting all NAICS codes")
        return opportunities

    filtered = []

    for opp in opportunities:
        naics_codes = []

        # Extract NAICS codes from various fields
        naics_code = opp.get("naicsCode") or opp.get("naics") or ""
        if naics_code:
            naics_codes.append(str(naics_code))

        # Check classification codes
        classifications = opp.get("classificationCode", [])
        if isinstance(classifications, str):
            naics_codes.append(classifications)
        elif isinstance(classifications, list):
            naics_codes.extend([str(c) for c in classifications])

        # Check if any NAICS code matches whitelist
        matches_whitelist = False
        for naics in naics_codes:
            naics = str(naics).strip()
            for whitelisted in NAICS_WHITELIST:
                if naics.startswith(whitelisted.strip()):
                    matches_whitelist = True
                    opp["matched_naics"] = naics
                    break
            if matches_whitelist:
                break

        if matches_whitelist:
            filtered.append(opp)

    logger.info(f"Filtered to {len(filtered)} opportunities matching NAICS whitelist")
    return filtered


def build_bid_pack_json(opportunity: dict[str, Any]) -> dict[str, Any]:
    """Build comprehensive bid pack JSON from opportunity data."""

    # Extract officer/contact information
    officers = opportunity.get("officers", [])
    primary_officer = officers[0] if officers else {}

    # Build comprehensive bid pack
    bid_pack = {
        # Basic opportunity info
        "Solicitation #": opportunity.get("solicitationNumber") or opportunity.get("id", ""),
        "Title": opportunity.get("title", ""),
        "Description": opportunity.get("description", "")[:2000],  # Limit description length
        "NAICS": opportunity.get("naicsCode") or opportunity.get("matched_naics", ""),
        "Due_Date": opportunity.get("responseDate") or opportunity.get("parsed_due_date", ""),
        "Status": opportunity.get("type", "Active"),
        "Link": opportunity.get("uiLink") or opportunity.get("link", ""),
        # Contact information
        "Officer": primary_officer.get("fullName", ""),
        "Email": primary_officer.get("email", ""),
        "Phone": primary_officer.get("phone", ""),
        "Office": primary_officer.get("office", ""),
        # Agency information
        "Agency": opportunity.get("department", ""),
        "Sub_Agency": opportunity.get("subTier", ""),
        "Office_Address": opportunity.get("officeAddress", {}).get("city", ""),
        # Opportunity details
        "Set_Aside": opportunity.get("typeOfSetAsideDescription", ""),
        "Competition_Type": opportunity.get("typeOfContractDescription", ""),
        "Place_of_Performance": opportunity.get("placeOfPerformance", {}).get("city", ""),
        # Financial information
        "Estimated_Value": opportunity.get("award", {}).get("amount", ""),
        "Contract_Award": opportunity.get("award", {}).get("date", ""),
        # Metadata
        "Source": opportunity.get("source", "SAM.gov"),
        "Opportunity_Type": opportunity.get("opportunity_type", ""),
        "Posted_Date": opportunity.get("postedDate", ""),
        "Modified_Date": opportunity.get("modifiedDate", ""),
        "Archive_Date": opportunity.get("archiveDate", ""),
        # Our tracking fields
        "Lead_Score": calculate_opportunity_score(opportunity),
        "Timestamp": datetime.utcnow().isoformat(),
        "UEI_Match": UEI in opportunity.get("awardee", {}).get("ueiSAM", "") if UEI else False,
        "CAGE_Match": CAGE_CODE in opportunity.get("awardee", {}).get("cageCode", "")
        if CAGE_CODE
        else False,
    }

    return bid_pack


def calculate_opportunity_score(opportunity: dict[str, Any]) -> int:
    """Calculate lead score for opportunity prioritization."""
    score = 0

    # Contact information available
    officers = opportunity.get("officers", [])
    if officers and officers[0].get("email"):
        score += 30
    if officers and officers[0].get("phone"):
        score += 20

    # Due date proximity (closer = higher score)
    due_date_str = opportunity.get("responseDate") or opportunity.get("parsed_due_date", "")
    if due_date_str:
        try:
            due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
            days_until_due = (due_date - datetime.utcnow().replace(tzinfo=due_date.tzinfo)).days
            if days_until_due <= 3:
                score += 25
            elif days_until_due <= 7:
                score += 15
        except:
            pass

    # Set-aside opportunities (often easier to win)
    set_aside = opportunity.get("typeOfSetAsideDescription", "").lower()
    if any(term in set_aside for term in ["small business", "8(a)", "hubzone", "wosb", "vosb"]):
        score += 20

    # Competition type
    competition = opportunity.get("typeOfContractDescription", "").lower()
    if "full and open" in competition:
        score += 10
    elif "limited" in competition:
        score += 15

    return score


def create_opportunity_dedup_key(opportunity: dict[str, Any]) -> str:
    """Create deduplication key for opportunity."""
    solicitation_num = opportunity.get("Solicitation #", "")
    if solicitation_num:
        return hashlib.sha256(solicitation_num.encode()).hexdigest()[:16]

    # Fallback to title + agency hash
    title = opportunity.get("Title", "")
    agency = opportunity.get("Agency", "")
    key_string = f"{title}|{agency}".lower().strip()
    return hashlib.sha256(key_string.encode()).hexdigest()[:16]


def send_govcon_outreach(opportunities: list[dict[str, Any]]) -> int:
    """Send outreach messages for high-scoring opportunities."""
    sent_count = 0

    # Sort by score and take top opportunities
    high_score_opps = [opp for opp in opportunities if opp.get("Lead_Score", 0) >= 40]
    high_score_opps.sort(key=lambda x: x.get("Lead_Score", 0), reverse=True)

    for opp in high_score_opps[:10]:  # Limit to top 10
        phone = opp.get("Phone")
        if phone and format_phone_number(phone):
            try:
                message_sid = send_govcon_message(format_phone_number(phone))
                if message_sid:
                    opp["Message_Sent"] = True
                    opp["Message_SID"] = message_sid
                    opp["Message_Timestamp"] = datetime.utcnow().isoformat()
                    sent_count += 1

                    # Rate limiting
                    import time

                    time.sleep(3)  # 3 second delay for GovCon

            except Exception as e:
                logger.warning(f"Failed to send GovCon message: {e}")

    logger.info(f"Sent GovCon outreach to {sent_count} opportunities")
    return sent_count


def run_govcon() -> int:
    """
    Run GovCon subtrap engine with comprehensive opportunity processing.

    Returns:
        Number of new opportunities processed
    """
    logger.info("Starting GovCon subtrap engine")

    try:
        # Fetch opportunities from multiple sources
        sam_opportunities = fetch_sam_opportunities()
        fpds_opportunities = fetch_fpds_feed()

        all_opportunities = sam_opportunities + fpds_opportunities
        logger.info(f"Fetched {len(all_opportunities)} total opportunities")

        # Apply filters in sequence
        filtered_opportunities = filter_combined_synopsis_solicitation(all_opportunities)
        filtered_opportunities = filter_by_due_date(filtered_opportunities)
        filtered_opportunities = filter_by_naics(filtered_opportunities)

        logger.info(f"After filtering: {len(filtered_opportunities)} opportunities remain")

        # Build bid packs
        bid_packs = []
        for opp in filtered_opportunities:
            try:
                bid_pack = build_bid_pack_json(opp)
                bid_packs.append(bid_pack)
            except Exception as e:
                logger.warning(f"Error building bid pack: {e}")
                continue

        # Deduplicate against existing records
        existing_records = fetch_all("GovCon_Opportunities")
        existing_dedup_keys = {
            r["fields"].get("dedup_key") for r in existing_records if r["fields"].get("dedup_key")
        }

        new_opportunities = []
        for bid_pack in bid_packs:
            dedup_key = create_opportunity_dedup_key(bid_pack)
            if dedup_key not in existing_dedup_keys:
                bid_pack["dedup_key"] = dedup_key
                new_opportunities.append(bid_pack)

        logger.info(f"Found {len(new_opportunities)} new opportunities after deduplication")

        # Write new opportunities to Airtable
        written_count = 0
        for opp in new_opportunities:
            try:
                result = safe_airtable_write("GovCon_Opportunities", opp, ["dedup_key"])
                if result:
                    written_count += 1
            except Exception as e:
                logger.error(f"Error writing opportunity to Airtable: {e}")
                continue

        # Send outreach messages
        if written_count > 0:
            message_count = send_govcon_outreach(new_opportunities)
            kpi_push("govcon_outreach", {"sent": message_count, "opportunities": written_count})

        # Log results
        post_ops(
            f"GovCon engine completed: {written_count} new opportunities, {len(all_opportunities)} total processed"
        )
        logger.info(f"GovCon engine completed: {written_count} new opportunities written")

        return written_count

    except Exception as e:
        logger.error(f"GovCon engine failed: {e}")
        post_error(f"GovCon engine failed: {str(e)}")
        return 0

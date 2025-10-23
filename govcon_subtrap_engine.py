import os
import requests
import datetime
import logging
from typing import List, Dict, Any, Optional
from airtable_utils import safe_airtable_write, fetch_all
from discord_utils import post_ops, post_error
from kpi import track_cycle_start, track_cycle_end, track_error
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
SAM_SEARCH_API = os.getenv("SAM_SEARCH_API", "https://api.sam.gov/prod/opportunities/v2/search")
FPDS_ATOM_FEED = os.getenv("FPDS_ATOM_FEED", "https://www.fpds.gov/ezsearch/FEEDS/ATOM?FEEDNAME=AWARD&q=")
NAICS_WHITELIST = os.getenv("NAICS_WHITELIST", "").split(",") if os.getenv("NAICS_WHITELIST") else []
UEI = os.getenv("UEI", "")
CAGE_CODE = os.getenv("CAGE_CODE", "")

class GovConError(Exception):
    """Custom exception for GovCon operations"""
    pass

def is_naics_whitelisted(naics_code: str) -> bool:
    """Check if NAICS code is in whitelist"""
    if not NAICS_WHITELIST or not naics_code:
        return True  # If no whitelist, allow all
    return naics_code in NAICS_WHITELIST

def is_due_within_days(due_date_str: str, days: int = 7) -> bool:
    """Check if due date is within specified days"""
    try:
        if not due_date_str:
            return False
        
        # Parse various date formats
        due_date = None
        for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S"]:
            try:
                due_date = datetime.datetime.strptime(due_date_str.split("T")[0], fmt).date()
                break
            except ValueError:
                continue
        
        if not due_date:
            return False
        
        cutoff_date = datetime.date.today() + datetime.timedelta(days=days)
        return due_date <= cutoff_date
        
    except Exception as e:
        logger.warning(f"Error parsing due date {due_date_str}: {e}")
        return False

def is_combined_synopsis_solicitation(opportunity_type: str, title: str) -> bool:
    """Check if opportunity is Combined Synopsis/Solicitation"""
    if not opportunity_type and not title:
        return False
    
    combined_keywords = ["combined", "synopsis", "solicitation", "rfp", "rfi", "rfq"]
    text_to_check = f"{opportunity_type} {title}".lower()
    
    return any(keyword in text_to_check for keyword in combined_keywords)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type((requests.exceptions.RequestException, GovConError))
)
def fetch_sam_opportunities() -> List[Dict[str, Any]]:
    """Fetch opportunities from SAM.gov with retry logic"""
    try:
        params = {
            "limit": 100,
            "sort": "-publishDate",
            "postedFrom": (datetime.date.today() - datetime.timedelta(days=14)).isoformat(),
            "postedTo": datetime.date.today().isoformat(),
            "noticeType": "presol,combine,mod",
            "status": "active"
        }
        
        response = requests.get(SAM_SEARCH_API, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        opportunities = data.get("opportunitiesData", [])
        
        logger.info(f"Fetched {len(opportunities)} opportunities from SAM.gov")
        return opportunities
        
    except Exception as e:
        logger.error(f"SAM.gov pull failed: {e}")
        post_error(f"SAM.gov pull failed: {e}")
        raise GovConError(f"SAM.gov data fetch failed: {e}")

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type((requests.exceptions.RequestException, GovConError))
)
def fetch_fpds_data() -> List[Dict[str, Any]]:
    """Fetch data from FPDS Atom feed with retry logic"""
    try:
        # Search for recent awards
        search_params = {
            "LAST_MOD_DATE": (datetime.date.today() - datetime.timedelta(days=7)).strftime("%m/%d/%Y"),
            "AWARD_TYPE": "A",
            "AWARD_AMOUNT": "10000.."
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in search_params.items()])
        url = f"{FPDS_ATOM_FEED}{query_string}"
        
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Parse Atom feed (simplified)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.text)
        
        awards = []
        for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
            title_elem = entry.find(".//{http://www.w3.org/2005/Atom}title")
            link_elem = entry.find(".//{http://www.w3.org/2005/Atom}link")
            
            if title_elem is not None and link_elem is not None:
                awards.append({
                    "title": title_elem.text,
                    "link": link_elem.get("href"),
                    "source": "FPDS"
                })
        
        logger.info(f"Fetched {len(awards)} awards from FPDS")
        return awards
        
    except Exception as e:
        logger.error(f"FPDS pull failed: {e}")
        post_error(f"FPDS pull failed: {e}")
        raise GovConError(f"FPDS data fetch failed: {e}")

def build_bid_pack_json(opportunity: Dict[str, Any]) -> Dict[str, Any]:
    """Build bid pack JSON for opportunity"""
    return {
        "solicitation_number": opportunity.get("solicitationNumber", ""),
        "title": opportunity.get("title", ""),
        "naics_code": opportunity.get("naicsCode", ""),
        "due_date": opportunity.get("responseDate", ""),
        "officer_name": opportunity.get("officers", [{}])[0].get("fullName", ""),
        "officer_email": opportunity.get("officers", [{}])[0].get("email", ""),
        "opportunity_type": opportunity.get("type", ""),
        "ui_link": opportunity.get("uiLink", ""),
        "description": opportunity.get("description", ""),
        "estimated_value": opportunity.get("estimatedValue", ""),
        "uei": UEI,
        "cage_code": CAGE_CODE,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

def filter_opportunities(opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter opportunities based on criteria"""
    filtered = []
    
    for opp in opportunities:
        # Check NAICS whitelist
        naics_code = opp.get("naicsCode", "")
        if not is_naics_whitelisted(naics_code):
            continue
        
        # Check if due within 7 days
        due_date = opp.get("responseDate", "")
        if not is_due_within_days(due_date, 7):
            continue
        
        # Check if Combined Synopsis/Solicitation
        opp_type = opp.get("type", "")
        title = opp.get("title", "")
        if not is_combined_synopsis_solicitation(opp_type, title):
            continue
        
        # Must have officer email
        officers = opp.get("officers", [])
        if not officers or not officers[0].get("email"):
            continue
        
        filtered.append(opp)
    
    logger.info(f"Filtered {len(opportunities)} opportunities to {len(filtered)} matching criteria")
    return filtered

def run_govcon() -> int:
    """Main GovCon engine execution"""
    try:
        track_cycle_start("GovCon")
        
        # Fetch opportunities from SAM.gov
        sam_opportunities = fetch_sam_opportunities()
        
        # Fetch additional data from FPDS
        fpds_data = fetch_fpds_data()
        
        # Filter opportunities
        filtered_opportunities = filter_opportunities(sam_opportunities)
        
        # Get existing opportunities for deduplication
        existing_records = fetch_all("GovCon_Opportunities")
        existing_ids = {r["fields"].get("Solicitation #") for r in existing_records}
        
        # Process new opportunities
        written_count = 0
        for opp in filtered_opportunities:
            solicitation_id = opp.get("solicitationNumber")
            if not solicitation_id or solicitation_id in existing_ids:
                continue
            
            # Build opportunity record
            officer = opp.get("officers", [{}])[0]
            opportunity_record = {
                "Solicitation #": solicitation_id,
                "Title": opp.get("title", ""),
                "NAICS": opp.get("naicsCode", ""),
                "Due_Date": opp.get("responseDate", ""),
                "Officer": officer.get("fullName", ""),
                "Email": officer.get("email", ""),
                "Status": opp.get("type", ""),
                "Link": opp.get("uiLink", ""),
                "Description": opp.get("description", ""),
                "Estimated_Value": opp.get("estimatedValue", ""),
                "Bid_Pack_JSON": str(build_bid_pack_json(opp)),
                "Source": "SAM.gov",
                "Timestamp": datetime.datetime.utcnow().isoformat(),
                "UEI": UEI,
                "CAGE_Code": CAGE_CODE
            }
            
            try:
                # Use solicitation number for deduplication
                key_fields = ["Solicitation #"]
                safe_airtable_write("GovCon_Opportunities", opportunity_record, key_fields)
                written_count += 1
                logger.info(f"Added opportunity: {solicitation_id}")
            except Exception as e:
                logger.error(f"Failed to write opportunity {solicitation_id}: {e}")
                track_error("GovCon", f"Failed to write opportunity {solicitation_id}: {e}")
        
        track_cycle_end("GovCon", written_count, success=True)
        post_ops(f"GovCon loop added {written_count} verified solicitations from {len(sam_opportunities)} total")
        
        logger.info(f"GovCon cycle completed: {written_count} opportunities written")
        return written_count
        
    except Exception as e:
        track_error("GovCon", str(e))
        post_error(f"GovCon loop failed: {e}")
        logger.error(f"GovCon cycle failed: {e}")
        return 0

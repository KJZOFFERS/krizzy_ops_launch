"""
GovCon Subtrap Engine - Pulls government contracting opportunities from SAM.gov and FPDS.
"""
import os
import requests
import datetime
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from airtable_utils import safe_airtable_write, fetch_all
from discord_utils import post_ops, post_err
from kpi import kpi_push
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class GovConProcessor:
    """Processes government contracting opportunities with filtering and enrichment."""
    
    def __init__(self):
        self.sam_api = os.getenv("SAM_SEARCH_API")
        self.sam_key = os.getenv("SAM_API_KEY")
        self.fpds_feed = os.getenv("FPDS_ATOM_FEED")
        self.naics_whitelist = self._load_naics_whitelist()
        self.uei = os.getenv("UEI")
        self.cage_code = os.getenv("CAGE_CODE")
        
        if not self.sam_api:
            raise ValueError("SAM_SEARCH_API environment variable is required")
    
    def _load_naics_whitelist(self) -> List[str]:
        """Load NAICS codes from environment variable."""
        naics_str = os.getenv("NAICS_WHITELIST", "")
        if naics_str:
            return [code.strip() for code in naics_str.split(",") if code.strip()]
        return []
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.RequestException)
    )
    def _fetch_sam_opportunities(self, days_back: int = 14) -> List[Dict[str, Any]]:
        """Fetch opportunities from SAM.gov API."""
        try:
            params = {
                "limit": 100,
                "api_key": self.sam_key,
                "sort": "-publishDate",
                "postedFrom": (datetime.date.today() - datetime.timedelta(days=days_back)).isoformat(),
                "postedTo": datetime.date.today().isoformat(),
                "noticeType": "Combined Synopsis/Solicitation,Presolicitation,Solicitation"
            }
            
            response = requests.get(self.sam_api, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return data.get("opportunitiesData", [])
            
        except Exception as e:
            kpi_push("error", {
                "error_type": "sam_fetch_error",
                "message": f"Failed to fetch SAM opportunities: {e}"
            })
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.RequestException)
    )
    def _fetch_fpds_data(self) -> List[Dict[str, Any]]:
        """Fetch data from FPDS ATOM feed."""
        try:
            if not self.fpds_feed:
                return []
            
            response = requests.get(self.fpds_feed, timeout=30)
            response.raise_for_status()
            
            # Parse ATOM feed
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.text)
            
            entries = []
            for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
                entry_data = {}
                for child in entry:
                    tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                    entry_data[tag] = child.text
                entries.append(entry_data)
            
            return entries
            
        except Exception as e:
            kpi_push("error", {
                "error_type": "fpds_fetch_error",
                "message": f"Failed to fetch FPDS data: {e}"
            })
            return []
    
    def _filter_opportunity(self, opportunity: Dict[str, Any]) -> bool:
        """Filter opportunities based on criteria."""
        try:
            # Check if it's a Combined Synopsis/Solicitation
            notice_type = opportunity.get("type", "").lower()
            if "combined synopsis" not in notice_type and "solicitation" not in notice_type:
                return False
            
            # Check due date (within 7 days)
            due_date_str = opportunity.get("responseDate", "")
            if due_date_str:
                try:
                    due_date = datetime.datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
                    days_until_due = (due_date - datetime.datetime.now()).days
                    if days_until_due > 7 or days_until_due < 0:
                        return False
                except ValueError:
                    return False
            
            # Check NAICS code
            naics_code = opportunity.get("naicsCode", "")
            if self.naics_whitelist and naics_code not in self.naics_whitelist:
                return False
            
            # Check for required contact information
            officers = opportunity.get("officers", [])
            if not officers or not officers[0].get("email"):
                return False
            
            return True
            
        except Exception as e:
            kpi_push("error", {
                "error_type": "filter_error",
                "message": f"Error filtering opportunity: {e}",
                "opportunity_id": opportunity.get("solicitationNumber", "unknown")
            })
            return False
    
    def _enrich_opportunity(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich opportunity with additional data."""
        try:
            # Generate source ID for deduplication
            source_id = hashlib.md5(
                f"{opportunity.get('solicitationNumber', '')}{opportunity.get('uiLink', '')}".encode()
            ).hexdigest()
            
            # Extract officer information
            officers = opportunity.get("officers", [])
            officer = officers[0] if officers else {}
            
            # Calculate days until due
            due_date_str = opportunity.get("responseDate", "")
            days_until_due = None
            if due_date_str:
                try:
                    due_date = datetime.datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
                    days_until_due = (due_date - datetime.datetime.now()).days
                except ValueError:
                    pass
            
            # Build bid pack JSON
            bid_pack = {
                "solicitation_number": opportunity.get("solicitationNumber", ""),
                "title": opportunity.get("title", ""),
                "naics_code": opportunity.get("naicsCode", ""),
                "due_date": due_date_str,
                "days_until_due": days_until_due,
                "officer_name": officer.get("fullName", ""),
                "officer_email": officer.get("email", ""),
                "officer_phone": officer.get("phone", ""),
                "agency": opportunity.get("department", ""),
                "sub_agency": opportunity.get("subTier", ""),
                "notice_type": opportunity.get("type", ""),
                "ui_link": opportunity.get("uiLink", ""),
                "description": opportunity.get("description", ""),
                "estimated_value": opportunity.get("awardAmount", ""),
                "uei": self.uei,
                "cage_code": self.cage_code,
                "created_at": datetime.datetime.utcnow().isoformat()
            }
            
            # Create Airtable record
            record = {
                "Solicitation #": opportunity.get("solicitationNumber", ""),
                "Title": opportunity.get("title", ""),
                "NAICS": opportunity.get("naicsCode", ""),
                "Due_Date": due_date_str,
                "Days_Until_Due": days_until_due,
                "Officer": officer.get("fullName", ""),
                "Email": officer.get("email", ""),
                "Phone": officer.get("phone", ""),
                "Agency": opportunity.get("department", ""),
                "Sub_Agency": opportunity.get("subTier", ""),
                "Status": opportunity.get("type", ""),
                "Link": opportunity.get("uiLink", ""),
                "Description": opportunity.get("description", ""),
                "Estimated_Value": opportunity.get("awardAmount", ""),
                "Bid_Pack_JSON": json.dumps(bid_pack),
                "Source": "SAM.gov",
                "source_id": source_id,
                "Timestamp": datetime.datetime.utcnow().isoformat()
            }
            
            return record
            
        except Exception as e:
            kpi_push("error", {
                "error_type": "enrichment_error",
                "message": f"Error enriching opportunity: {e}",
                "opportunity_id": opportunity.get("solicitationNumber", "unknown")
            })
            return {}
    
    def _deduplicate_opportunities(self, new_opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate opportunities based on solicitation number."""
        try:
            existing_opportunities = fetch_all("GovCon_Opportunities")
            existing_ids = {opp["fields"].get("Solicitation #") for opp in existing_opportunities}
            
            unique_opportunities = []
            for opp in new_opportunities:
                solicitation_id = opp.get("Solicitation #")
                if solicitation_id and solicitation_id not in existing_ids:
                    unique_opportunities.append(opp)
            
            return unique_opportunities
            
        except Exception as e:
            kpi_push("error", {
                "error_type": "deduplication_error",
                "message": f"Failed to deduplicate opportunities: {e}"
            })
            return new_opportunities
    
    def run_govcon(self) -> int:
        """Main GovCon processing function."""
        try:
            kpi_push("cycle_start", {"engine": "govcon"})
            
            # Fetch opportunities from SAM.gov
            sam_opportunities = self._fetch_sam_opportunities()
            
            # Filter opportunities
            filtered_opportunities = [
                opp for opp in sam_opportunities 
                if self._filter_opportunity(opp)
            ]
            
            # Enrich opportunities
            enriched_opportunities = []
            for opp in filtered_opportunities:
                enriched = self._enrich_opportunity(opp)
                if enriched:
                    enriched_opportunities.append(enriched)
            
            # Deduplicate opportunities
            unique_opportunities = self._deduplicate_opportunities(enriched_opportunities)
            
            # Write to Airtable
            opportunities_written = 0
            for opp in unique_opportunities:
                success, record_id = safe_airtable_write(
                    "GovCon_Opportunities",
                    opp,
                    key_fields=["Solicitation #", "source_id"]
                )
                if success:
                    opportunities_written += 1
            
            # Log results
            post_ops(f"GovCon cycle completed: {opportunities_written} opportunities written from {len(sam_opportunities)} total")
            
            kpi_push("cycle_end", {
                "engine": "govcon",
                "count": opportunities_written,
                "total_fetched": len(sam_opportunities),
                "filtered": len(filtered_opportunities),
                "unique": len(unique_opportunities)
            })
            
            return opportunities_written
            
        except Exception as e:
            kpi_push("error", {
                "error_type": "govcon_cycle_error",
                "message": f"GovCon cycle failed: {e}"
            })
            post_err(f"GovCon cycle failed: {e}")
            return 0


# Global processor instance (lazy initialization)
_govcon_processor_instance = None

def get_govcon_processor():
    """Get or create GovCon processor instance."""
    global _govcon_processor_instance
    if _govcon_processor_instance is None:
        _govcon_processor_instance = GovConProcessor()
    return _govcon_processor_instance

# For backward compatibility
class GovConProcessorProxy:
    def __getattr__(self, name):
        return getattr(get_govcon_processor(), name)

govcon_processor = GovConProcessorProxy()


def run_govcon() -> int:
    """Convenience function for running GovCon processing."""
    return govcon_processor.run_govcon()

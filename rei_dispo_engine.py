"""
REI Disposition Engine - Pulls and enriches real estate leads from multiple sources.
"""
import requests
import datetime
import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple
from airtable_utils import safe_airtable_write, fetch_all
from discord_utils import post_ops, post_err
from twilio_utils import send_msg
from kpi import kpi_push
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class REILeadProcessor:
    """Processes REI leads with enrichment and deduplication."""
    
    def __init__(self):
        self.sources = {
            "zillow": "https://www.zillow.com/homes/for_sale/?format=json",
            "craigslist": "https://www.craigslist.org/search/rea?format=rss",
            "realtor": "https://www.realtor.com/api/v1/hulk?client_id=rdc-x&schema=vesta"
        }
        
        # Buyer database for Twilio messaging
        self.buyers = self._load_buyers()
    
    def _load_buyers(self) -> List[Dict[str, Any]]:
        """Load buyers from Airtable for SMS notifications."""
        try:
            buyers = fetch_all("Buyers")
            return [buyer["fields"] for buyer in buyers if buyer["fields"].get("Phone")]
        except Exception as e:
            kpi_push("error", {
                "error_type": "buyer_load_error",
                "message": f"Failed to load buyers: {e}"
            })
            return []
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.RequestException)
    )
    def _fetch_source_data(self, source: str, url: str) -> Optional[Dict[str, Any]]:
        """Fetch data from source with retry logic."""
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            if source == "craigslist":
                import xml.etree.ElementTree as ET
                return ET.fromstring(response.text)
            else:
                return response.json()
        except Exception as e:
            kpi_push("error", {
                "error_type": "source_fetch_error",
                "message": f"Failed to fetch from {source}: {e}",
                "url": url
            })
            raise
    
    def _enrich_lead(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich lead with additional data and validation."""
        # Generate source ID for deduplication
        source_id = hashlib.md5(
            f"{lead.get('Source_URL', '')}{lead.get('Address', '')}".encode()
        ).hexdigest()
        
        # Add enrichment fields
        lead.update({
            "source_id": source_id,
            "enriched_at": datetime.datetime.utcnow().isoformat(),
            "lead_score": self._calculate_lead_score(lead),
            "contact_hash": self._generate_contact_hash(lead)
        })
        
        return lead
    
    def _calculate_lead_score(self, lead: Dict[str, Any]) -> int:
        """Calculate lead quality score (0-100)."""
        score = 0
        
        # Contact information
        if lead.get("Phone"):
            score += 30
        if lead.get("Email"):
            score += 20
        
        # Property information
        if lead.get("Price") and str(lead.get("Price")).replace(",", "").replace("$", "").isdigit():
            score += 25
        
        if lead.get("Address"):
            score += 15
        
        # Source quality
        if "zillow" in lead.get("Source_URL", "").lower():
            score += 10
        
        return min(score, 100)
    
    def _generate_contact_hash(self, lead: Dict[str, Any]) -> str:
        """Generate hash for contact deduplication."""
        phone = lead.get("Phone", "").replace("-", "").replace("(", "").replace(")", "").replace(" ", "")
        email = lead.get("Email", "").lower().strip()
        
        if phone or email:
            return hashlib.md5(f"{phone}{email}".encode()).hexdigest()
        return ""
    
    def parse_zillow(self) -> List[Dict[str, Any]]:
        """Parse Zillow listings."""
        try:
            data = self._fetch_source_data("zillow", self.sources["zillow"])
            if not data:
                return []
            
            leads = []
            for item in data.get("props", [])[:20]:
                if not item.get("address") or not item.get("price"):
                    continue
                
                lead = {
                    "Address": item.get("address"),
                    "City": item.get("city"),
                    "State": item.get("state"),
                    "Zip": item.get("zipcode"),
                    "Price": item.get("price"),
                    "ARV": item.get("price"),  # Use price as ARV for now
                    "Agent": item.get("brokerName", ""),
                    "Phone": item.get("brokerPhone", ""),
                    "Email": item.get("brokerEmail", ""),
                    "Source_URL": f"https://www.zillow.com{item.get('detailUrl', '')}",
                    "Source": "Zillow",
                    "Timestamp": datetime.datetime.utcnow().isoformat()
                }
                
                # Enrich lead
                lead = self._enrich_lead(lead)
                leads.append(lead)
            
            return leads
            
        except Exception as e:
            post_err(f"Zillow parsing failed: {e}")
            return []
    
    def parse_craigslist(self) -> List[Dict[str, Any]]:
        """Parse Craigslist listings."""
        try:
            root = self._fetch_source_data("craigslist", self.sources["craigslist"])
            if root is None:
                return []
            
            leads = []
            for item in root.findall(".//item")[:10]:
                title = item.findtext("title", "")
                if not title:
                    continue
                
                lead = {
                    "Address": title,
                    "City": "",
                    "State": "",
                    "Zip": "",
                    "Price": "",
                    "ARV": "",
                    "Agent": "",
                    "Phone": "",
                    "Email": "",
                    "Source_URL": item.findtext("link", ""),
                    "Source": "Craigslist",
                    "Timestamp": datetime.datetime.utcnow().isoformat()
                }
                
                # Enrich lead
                lead = self._enrich_lead(lead)
                leads.append(lead)
            
            return leads
            
        except Exception as e:
            post_err(f"Craigslist parsing failed: {e}")
            return []
    
    def deduplicate_leads(self, new_leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate leads based on source_id and contact_hash."""
        try:
            existing_leads = fetch_all("Leads_REI")
            existing_source_ids = {lead["fields"].get("source_id") for lead in existing_leads}
            existing_contact_hashes = {lead["fields"].get("contact_hash") for lead in existing_leads}
            
            unique_leads = []
            for lead in new_leads:
                source_id = lead.get("source_id")
                contact_hash = lead.get("contact_hash")
                
                if (source_id not in existing_source_ids and 
                    contact_hash not in existing_contact_hashes and
                    contact_hash):  # Must have contact info
                    unique_leads.append(lead)
            
            return unique_leads
            
        except Exception as e:
            kpi_push("error", {
                "error_type": "deduplication_error",
                "message": f"Failed to deduplicate leads: {e}"
            })
            return new_leads
    
    def send_buyer_notifications(self, leads: List[Dict[str, Any]]) -> int:
        """Send SMS notifications to buyers about new leads."""
        if not leads or not self.buyers:
            return 0
        
        notifications_sent = 0
        
        for buyer in self.buyers:
            try:
                # Send notification for each high-quality lead
                for lead in leads:
                    if lead.get("lead_score", 0) >= 70:  # Only high-quality leads
                        success, _ = send_msg(
                            to=buyer["Phone"],
                            title=f"New REI Lead: {lead.get('Address', 'Unknown')}",
                            due_date="Immediate",
                            custom_content=f"New lead: {lead.get('Address')} - ${lead.get('Price', 'N/A')} - {lead.get('Source_URL', '')}"
                        )
                        if success:
                            notifications_sent += 1
                        
                        # Limit notifications per buyer
                        if notifications_sent >= 3:
                            break
                
            except Exception as e:
                kpi_push("error", {
                    "error_type": "notification_error",
                    "message": f"Failed to send notification to buyer: {e}",
                    "buyer_phone": buyer.get("Phone", "unknown")
                })
        
        return notifications_sent
    
    def run_rei(self) -> int:
        """Main REI processing function."""
        try:
            kpi_push("cycle_start", {"engine": "rei"})
            
            # Parse leads from all sources
            zillow_leads = self.parse_zillow()
            craigslist_leads = self.parse_craigslist()
            
            all_leads = zillow_leads + craigslist_leads
            
            # Deduplicate leads
            unique_leads = self.deduplicate_leads(all_leads)
            
            # Filter for leads with contact information
            qualified_leads = [
                lead for lead in unique_leads 
                if lead.get("Phone") or lead.get("Email")
            ]
            
            # Write to Airtable
            leads_written = 0
            for lead in qualified_leads:
                success, record_id = safe_airtable_write(
                    "Leads_REI", 
                    lead, 
                    key_fields=["source_id", "contact_hash"]
                )
                if success:
                    leads_written += 1
            
            # Send buyer notifications
            notifications_sent = self.send_buyer_notifications(qualified_leads)
            
            # Log results
            post_ops(f"REI cycle completed: {leads_written} leads written, {notifications_sent} notifications sent")
            
            kpi_push("cycle_end", {
                "engine": "rei",
                "count": leads_written,
                "notifications_sent": notifications_sent,
                "total_parsed": len(all_leads),
                "unique_leads": len(unique_leads)
            })
            
            return leads_written
            
        except Exception as e:
            kpi_push("error", {
                "error_type": "rei_cycle_error",
                "message": f"REI cycle failed: {e}"
            })
            post_err(f"REI cycle failed: {e}")
            return 0


# Global processor instance
rei_processor = REILeadProcessor()


def run_rei() -> int:
    """Convenience function for running REI processing."""
    return rei_processor.run_rei()

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Buyer:
    """Represents a real estate buyer/investor"""

    # Identity
    buyer_id: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None

    # Preferences
    market_city: Optional[str] = None
    market_state: Optional[str] = None
    zip_codes: Optional[List[str]] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    rehab_appetite: Optional[str] = None  # "LIGHT", "MODERATE", "HEAVY"
    strategy: Optional[str] = None  # "FLIP", "RENTAL", "WHOLESALE"

    # Performance metrics
    tier: str = "C"  # A, B, C
    response_rate: float = 0.0
    close_rate: float = 0.0
    avg_response_time_hours: Optional[float] = None
    total_deals_closed: int = 0
    total_contacted: int = 0

    # Compliance
    last_contacted: Optional[datetime] = None
    opt_out: bool = False

    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    notes: Optional[str] = None

    def to_airtable_fields(self) -> Dict[str, Any]:
        """Convert to Airtable fields dict"""
        fields = {
            "Buyer_ID": self.buyer_id,
            "Name": self.name,
            "Tier": self.tier,
            "Response_Rate": self.response_rate,
            "Close_Rate": self.close_rate,
            "Total_Deals_Closed": self.total_deals_closed,
            "Total_Contacted": self.total_contacted,
            "Opt_Out": self.opt_out,
        }

        if self.phone:
            fields["Phone"] = self.phone
        if self.email:
            fields["Email"] = self.email
        if self.market_city:
            fields["Market_City"] = self.market_city
        if self.market_state:
            fields["Market_State"] = self.market_state
        if self.zip_codes:
            fields["ZIP_Codes"] = ",".join(self.zip_codes)
        if self.min_price is not None:
            fields["Min_Price"] = self.min_price
        if self.max_price is not None:
            fields["Max_Price"] = self.max_price
        if self.rehab_appetite:
            fields["Rehab_Appetite"] = self.rehab_appetite
        if self.strategy:
            fields["Strategy"] = self.strategy
        if self.notes:
            fields["Notes"] = self.notes

        return fields

    @classmethod
    def from_airtable_record(cls, record: Dict[str, Any]) -> "Buyer":
        """Create Buyer from Airtable record"""
        fields = record.get("fields", {})

        zip_codes = None
        if fields.get("ZIP_Codes"):
            zip_codes = [z.strip() for z in fields["ZIP_Codes"].split(",")]

        return cls(
            buyer_id=fields.get("Buyer_ID", ""),
            name=fields.get("Name", ""),
            phone=fields.get("Phone"),
            email=fields.get("Email"),
            market_city=fields.get("Market_City"),
            market_state=fields.get("Market_State"),
            zip_codes=zip_codes,
            min_price=fields.get("Min_Price"),
            max_price=fields.get("Max_Price"),
            rehab_appetite=fields.get("Rehab_Appetite"),
            strategy=fields.get("Strategy"),
            tier=fields.get("Tier", "C"),
            response_rate=fields.get("Response_Rate", 0.0),
            close_rate=fields.get("Close_Rate", 0.0),
            avg_response_time_hours=fields.get("Avg_Response_Time_Hours"),
            total_deals_closed=fields.get("Total_Deals_Closed", 0),
            total_contacted=fields.get("Total_Contacted", 0),
            opt_out=fields.get("Opt_Out", False),
            notes=fields.get("Notes"),
        )

from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Deal:
    """Represents a real estate deal"""

    # Identity
    external_id: str
    source: str

    # Property details
    address: str
    city: str
    state: str
    zip_code: str

    # Financial
    arv: Optional[float] = None
    asking: Optional[float] = None
    repairs: Optional[float] = None

    # Computed metrics
    mao: Optional[float] = None
    spread: Optional[float] = None
    spread_ratio: Optional[float] = None

    # Metadata
    seller_name: Optional[str] = None
    seller_phone: Optional[str] = None
    seller_email: Optional[str] = None
    raw_payload: Optional[str] = None

    # Lifecycle
    status: str = "NEW"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Scoring
    equity_score: Optional[float] = None
    strategy: Optional[str] = None  # "FLIP", "RENTAL", "WHOLESALE", "TRASH"
    risk_flags: Optional[str] = None

    def to_airtable_fields(self) -> Dict[str, Any]:
        """Convert to Airtable fields dict"""
        fields = {
            "External_Id": self.external_id,
            "Source": self.source,
            "Address": self.address,
            "City": self.city,
            "State": self.state,
            "ZIP": self.zip_code,
            "Status": self.status,
        }

        if self.arv is not None:
            fields["ARV"] = self.arv
        if self.asking is not None:
            fields["Asking"] = self.asking
        if self.repairs is not None:
            fields["Repairs"] = self.repairs
        if self.spread is not None:
            fields["Spread"] = self.spread
        if self.seller_name:
            fields["Name"] = self.seller_name
        if self.raw_payload:
            fields["Raw_Payload"] = self.raw_payload

        return fields

    @classmethod
    def from_airtable_record(cls, record: Dict[str, Any]) -> "Deal":
        """Create Deal from Airtable record"""
        fields = record.get("fields", {})

        return cls(
            external_id=fields.get("External_Id", ""),
            source=fields.get("Source", ""),
            address=fields.get("Address", ""),
            city=fields.get("City", ""),
            state=fields.get("State", ""),
            zip_code=fields.get("ZIP", ""),
            arv=fields.get("ARV"),
            asking=fields.get("Asking"),
            repairs=fields.get("Repairs"),
            spread=fields.get("Spread"),
            seller_name=fields.get("Name"),
            raw_payload=fields.get("Raw_Payload"),
            status=fields.get("Status", "NEW"),
        )

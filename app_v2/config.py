import json
import os
from typing import Any, Dict, List, Optional

# Environment variables
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY") or os.environ.get("AIRTABLE_PAT")
AIRTABLE_PAT = AIRTABLE_API_KEY
AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID") or "appIe21nS9Z9ahV7V"
DISCORD_WEBHOOK_OPS = os.environ.get("DISCORD_WEBHOOK_OPS")
DISCORD_WEBHOOK_ERRORS = os.environ.get("DISCORD_WEBHOOK_ERRORS")
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_MESSAGING_SERVICE_SID = os.environ.get("TWILIO_MESSAGING_SERVICE_SID")
GMAIL_CREDENTIALS_JSON = os.environ.get("GMAIL_CREDENTIALS_JSON")
GMAIL_TOKEN_JSON = os.environ.get("GMAIL_TOKEN_JSON")

# Ops + environment
ENVIRONMENT = os.environ.get("ENVIRONMENT", "local")
INIT_KEY = os.environ.get("INIT_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")

# SAM.gov / GovCon feed
SAM_API_KEY = os.environ.get("SAM_API_KEY")
GOVCON_PTYPE = os.environ.get("GOVCON_PTYPE")
GOVCON_NAICS = os.environ.get("GOVCON_NAICS")
GOVCON_SETASIDE = os.environ.get("GOVCON_SETASIDE")
GOVCON_RDL_FROM = os.environ.get("GOVCON_RDL_FROM")
GOVCON_RDL_TO = os.environ.get("GOVCON_RDL_TO")

# REI feed
REI_SOURCES_JSON = os.environ.get("REI_SOURCES_JSON")


def get_naics_codes() -> List[str]:
    """Parse GOVCON_NAICS env into a list (comma-separated)."""
    if not GOVCON_NAICS:
        return []
    if "," in GOVCON_NAICS:
        return [code.strip() for code in GOVCON_NAICS.split(",") if code.strip()]
    return [GOVCON_NAICS.strip()]


def get_rei_sources() -> List[Dict[str, Any]]:
    """Parse REI_SOURCES_JSON into a list of sources."""
    if not REI_SOURCES_JSON:
        return []
    try:
        parsed = json.loads(REI_SOURCES_JSON)
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
    except json.JSONDecodeError:
        return []
    return []

# Airtable tables
TABLE_INBOUND_REI = "Inbound_REI_Raw"
TABLE_LEADS_REI = "Leads_REI"
TABLE_BUYERS = "REI_Buyers"
TABLE_GOVCON = "GovCon Opportunities"
TABLE_OUTBOUND_LOG = "Outbound_Log"
TABLE_MARKET_INTEL = "Market_Intel"

# Engine intervals (seconds) - defaults, will be adjusted dynamically
DEFAULT_INTERVALS: Dict[str, int] = {
    "input": 60,           # 1 min - check Gmail, scrapers
    "underwriting": 120,   # 2 min - score deals
    "buyer": 180,          # 3 min - match and blast
    "outbound_control": 300,  # 5 min - throttle management
    "buyer_performance": 600,  # 10 min - update buyer scores
    "market_intel": 900,   # 15 min - update ZIP stats
    "govcon": 1800,        # 30 min - check opportunities
}

# Dynamic interval bounds (min, max)
INTERVAL_BOUNDS: Dict[str, tuple] = {
    "input": (30, 300),
    "underwriting": (60, 600),
    "buyer": (120, 900),
    "outbound_control": (180, 1800),
    "buyer_performance": (300, 3600),
    "market_intel": (600, 7200),
    "govcon": (900, 7200),
}

# Underwriting thresholds
MAO_MULTIPLIER = 0.70
MIN_SPREAD_RATIO = 0.05  # 5%
HIGH_POTENTIAL_SPREAD = 50000

# Buyer matching weights
BUYER_MATCH_WEIGHTS = {
    "zip_match": 0.4,
    "price_range": 0.3,
    "past_responsiveness": 0.2,
    "rehab_appetite": 0.1,
}

# Outbound control
DAILY_SMS_LIMIT = 100
MIN_REPLY_RATE = 0.05  # 5%
THROTTLE_REPLY_THRESHOLD = 0.03  # 3%

# Market intelligence
ZIP_VELOCITY_THRESHOLD = 5  # leads per day
HOT_ZIP_THRESHOLD = 10
COLD_ZIP_THRESHOLD = 1

# GovCon filters
GOVCON_NAICS_WHITELIST = ["541330", "541511", "541512", "541519"]  # IT consulting
GOVCON_MAX_DAYS_UNTIL_DEADLINE = 30
GOVCON_MIN_VALUE = 50000

# System health
HEARTBEAT_INTERVAL = 300  # 5 min
THREAD_RESTART_DELAY = 10
MAX_CONSECUTIVE_ERRORS = 5

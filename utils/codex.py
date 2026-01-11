import os
from dataclasses import dataclass
from typing import Optional, List


class CodexError(Exception):
    pass


def _req(name: str) -> str:
    v = os.getenv(name, "").strip()
    if not v:
        raise CodexError(f"Missing required env var: {name}")
    return v


def _opt(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass(frozen=True)
class Codex:
    # Core
    APP_ENV: str
    INIT_KEY: str

    # DB
    DATABASE_URL: str

    # Airtable
    AIRTABLE_PAT: str
    AIRTABLE_BASE_ID: str

    # Tables
    LEADS_REI_TABLE_ID: str
    GOVCON_OPPS_TABLE_ID: str

    # Merge keys (field IDs, not names)
    REI_MERGE_FIELD_ID: str
    GOVCON_MERGE_FIELD_ID: str

    # Buyers (for money loop)
    BUYERS_TABLE_ID: str
    BUYER_PHONE_FIELD_ID: str  # fieldId of phone column

    # Twilio (optional but required for outbound)
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_MESSAGING_SERVICE_SID: str

    # Guardrails
    OUTBOUND_CAP_PER_RUN: int
    QUIET_HOURS_LOCAL: str  # "21:00-08:00" in America/New_York

    @staticmethod
    def load() -> "Codex":
        # Required in all modes
        app_env = _opt("APP_ENV", "prod")
        init_key = _req("INIT_KEY")
        db = _req("DATABASE_URL")

        # Airtable
        pat = _req("AIRTABLE_PAT")
        base = _req("AIRTABLE_BASE_ID")

        # Tables + merge field IDs
        leads_rei = _req("LEADS_REI_TABLE_ID")
        govcon = _req("GOVCON_OPPS_TABLE_ID")
        rei_merge = _req("REI_MERGE_FIELD_ID")
        gov_merge = _req("GOVCON_MERGE_FIELD_ID")

        # Buyers loop
        buyers = _req("BUYERS_TABLE_ID")
        buyer_phone_field = _req("BUYER_PHONE_FIELD_ID")

        # Twilio
        tw_sid = _req("TWILIO_ACCOUNT_SID")
        tw_token = _req("TWILIO_AUTH_TOKEN")
        tw_ms = _req("TWILIO_MESSAGING_SERVICE_SID")

        cap = int(_opt("OUTBOUND_CAP_PER_RUN", "200") or "200")
        qh = _opt("QUIET_HOURS_LOCAL", "21:00-08:00")

        return Codex(
            APP_ENV=app_env,
            INIT_KEY=init_key,
            DATABASE_URL=db,
            AIRTABLE_PAT=pat,
            AIRTABLE_BASE_ID=base,
            LEADS_REI_TABLE_ID=leads_rei,
            GOVCON_OPPS_TABLE_ID=govcon,
            REI_MERGE_FIELD_ID=rei_merge,
            GOVCON_MERGE_FIELD_ID=gov_merge,
            BUYERS_TABLE_ID=buyers,
            BUYER_PHONE_FIELD_ID=buyer_phone_field,
            TWILIO_ACCOUNT_SID=tw_sid,
            TWILIO_AUTH_TOKEN=tw_token,
            TWILIO_MESSAGING_SERVICE_SID=tw_ms,
            OUTBOUND_CAP_PER_RUN=cap,
            QUIET_HOURS_LOCAL=qh,
        )

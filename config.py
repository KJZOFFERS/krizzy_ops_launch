# FILE: config.py
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import List

def _split_list(v: str | None) -> List[str]:
    if not v:
        return []
    return [x.strip() for x in v.split(",") if x.strip()]

@dataclass(frozen=True)
class _CFG:
    SERVICE_NAME: str
    ENV: str

    # Discord (supports comma-separated lists)
    DISCORD_WEBHOOK_OPS: List[str]
    DISCORD_WEBHOOK_ERRORS: List[str]

    # Airtable
    AIRTABLE_API_KEY: str | None
    AIRTABLE_BASE_ID: str | None
    AIRTABLE_TABLE_LEADS: str
    AIRTABLE_TABLE_BUYERS: str
    AIRTABLE_TABLE_GOVCON: str
    AIRTABLE_TABLE_KPI_LOG: str

    # Optional n8n
    N8N_REI_URL: str | None
    N8N_GOVCON_URL: str | None
    N8N_API_KEY: str | None

def _load() -> _CFG:
    return _CFG(
        SERVICE_NAME=os.getenv("SERVICE_NAME", "krizzy_ops_web"),
        ENV=os.getenv("ENV", "production"),
        DISCORD_WEBHOOK_OPS=_split_list(os.getenv("DISCORD_OPS_WEBHOOK_URL", "")),
        DISCORD_WEBHOOK_ERRORS=_split_list(os.getenv("DISCORD_ERRORS_WEBHOOK_URL", "")),
        AIRTABLE_API_KEY=os.getenv("AIRTABLE_API_KEY"),
        AIRTABLE_BASE_ID=os.getenv("AIRTABLE_BASE_ID"),
        AIRTABLE_TABLE_LEADS=os.getenv("AIRTABLE_TABLE_LEADS", "Leads_REI"),
        AIRTABLE_TABLE_BUYERS=os.getenv("AIRTABLE_TABLE_BUYERS", "Buyers"),
        AIRTABLE_TABLE_GOVCON=os.getenv("AIRTABLE_TABLE_GOVCON", "GovCon_Opportunities"),
        AIRTABLE_TABLE_KPI_LOG=os.getenv("AIRTABLE_TABLE_KPI_LOG", "KPI_Log"),
        N8N_REI_URL=os.getenv("N8N_REI_URL"),
        N8N_GOVCON_URL=os.getenv("N8N_GOVCON_URL"),
        N8N_API_KEY=os.getenv("N8N_API_KEY"),
    )

CFG = _load()


CFG = _load()

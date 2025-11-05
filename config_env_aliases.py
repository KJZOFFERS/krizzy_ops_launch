# FILE: config_env_aliases.py
import os

def _alias(dst: str, *srcs: str):
    if os.getenv(dst):
        return
    for s in srcs:
        v = os.getenv(s)
        if v:
            os.environ[dst] = v
            return

# Discord aliases
_alias("DISCORD_OPS_WEBHOOK_URL", "DISCORD_WEBHOOK_OPS")
_alias("DISCORD_ERRORS_WEBHOOK_URL", "DISCORD_WEBHOOK_ERRORS")

# Airtable core
# AIRTABLE_API_KEY, AIRTABLE_BASE_ID are canonical

# Airtable table names
_alias("AIRTABLE_TABLE_LEADS", "AT_TABLE_LEADS_REI")
_alias("AIRTABLE_TABLE_BUYERS", "AT_TABLE_BUYERS")
_alias("AIRTABLE_TABLE_GOVCON", "AT_TABLE_GOVCON")
_alias("AIRTABLE_TABLE_KPI_LOG", "AT_TABLE_KPI")

# GovCon config
_alias("GOVCON_NAICS", "NAICS_WHITELIST")
_alias("GOVCON_STATES", "STATES_WHITELIST")
_alias("GOVCON_POSTED_DAYS", "GOVCON_POSTED_DAYS")
_alias("GOVCON_LIMIT", "GOVCON_LIMIT")

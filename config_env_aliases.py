import os
def _alias(dst, *srcs):
    if os.getenv(dst): return
    for s in srcs:
        v = os.getenv(s)
        if v:
            os.environ[dst] = v; return

_alias("DISCORD_OPS_WEBHOOK_URL", "DISCORD_WEBHOOK_OPS")
_alias("DISCORD_ERRORS_WEBHOOK_URL", "DISCORD_WEBHOOK_ERRORS")
_alias("AIRTABLE_TABLE_LEADS", "AT_TABLE_LEADS_REI")
_alias("AIRTABLE_TABLE_BUYERS", "AT_TABLE_BUYERS")
_alias("AIRTABLE_TABLE_GOVCON", "AT_TABLE_GOVCON")
_alias("AIRTABLE_TABLE_KPI_LOG", "AT_TABLE_KPI")
_alias("GOVCON_NAICS", "NAICS_WHITELIST")
_alias("GOVCON_POSTED_DAYS", "GOVCON_POSTED_DAYS")
_alias("GOVCON_LIMIT", "GOVCON_LIMIT")

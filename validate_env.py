import os, sys

REQUIRED = [
    "AIRTABLE_API_KEY",
    "AIRTABLE_BASE_ID",
    "TABLE_KPI_LOG",
    "DISCORD_WEBHOOK_OPS",
    "DISCORD_WEBHOOK_ERRORS",
]

def validate_env():
    missing = [v for v in REQUIRED if not os.getenv(v)]
    if missing:
        sys.exit(f"Missing env vars: {', '.join(missing)}")

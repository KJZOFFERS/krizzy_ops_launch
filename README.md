# KRIZZY OPS Bots

Single-file automation for:

- `REI_DISPO_ENGINE` — texts REI leads from Airtable (`Leads_REI`) via Twilio.
- `GOVCON_SUBTRAP_ENGINE` — pulls SAM.gov opps into Airtable (`GovCon_Opportunities`) and posts digests to Discord.
- `KRIZZY_PLATFORM` health checks — Airtable, Twilio, Discord.

## Files

- `krizzy_bots.py` — main and only Python file. Contains:
  - Airtable, Twilio, Discord helpers
  - REI ingestion + SMS loop
  - GovCon SAM.gov ingestion + digest loop
  - Health checks
- `.env.example` — environment variables you must set.

## Environment

Copy `.env.example` to `.env` and fill in real values:

```bash
AIRTABLE_API_KEY=...
AIRTABLE_BASE_ID=...
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_MESSAGING_SERVICE_SID=...
DISCORD_WEBHOOK_OPS=...
DISCORD_WEBHOOK_ERRORS=...

REI_SMS_MAX_PER_RUN=30
GOVCON_MAX_OPPS_PER_DIGEST=20

REI_INGEST_MODE=free_feed      # or: disabled
FREE_REI_FEED_URL=https://your-open-data-or-csv-url
FREE_REI_FEED_FORMAT=csv       # csv or json
FREE_REI_FEED_SOURCE_NAME=County_Open_Data

GOVCON_INGEST_MODE=sam_api     # or: disabled
GOVCON_SAM_API_KEY=...
GOVCON_NAICS_WHITELIST=541511,541512
GOVCON_POSTED_DAYS_BACK=7
GOVCON_RDL_DAYS_AHEAD=30
GOVCON_MAX_RECORDS_TOTAL=100

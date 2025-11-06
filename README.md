python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# set envs (see .env.example below)
export SERVICE_NAME=krizzy_ops_web
export ADMIN_TOKEN=replace-me
export DISCORD_OPS_WEBHOOK_URL=...
export DISCORD_ERRORS_WEBHOOK_URL=...
export AIRTABLE_API_KEY=...
export AIRTABLE_BASE_ID=appXXXXXXXXXXXXXX
export AT_TABLE_LEADS_REI=Leads_REI
export AT_TABLE_BUYERS=Buyers
export AT_TABLE_GOVCON=GovCon_Opportunities
export AT_TABLE_KPI=KPI_Log
export OPENAI_API_KEY=...
export OPENAI_MODEL=gpt-4o-mini
export OPENAI_TIMEOUT_S=20

uvicorn main:app --host 0.0.0.0 --port 8080

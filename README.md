# KRIZZY OPS v3.0.0

Production-ready real estate investment (REI) and government contracting (GovCon) opportunity tracking system.

## Features

### 🏠 REI Disposition Engine
- Pulls seller/buyer data from Zillow and Craigslist
- Enriches leads with contact information
- Deduplicates using source_id and phone/email hash
- Writes to Airtable Leads_REI table
- Sends Twilio SMS notifications with content rotation

### 🏛️ GovCon Subtrap Engine
- Pulls opportunities from SAM.gov and FPDS
- Filters for Combined Synopsis/Solicitation
- Due date within 7 days
- NAICS code whitelist filtering
- Builds bid-pack JSON
- Writes to Airtable GovCon_Opportunities table

### 🔧 System Components
- **Health Endpoint**: `/health` returns system status
- **Watchdog**: Restarts failed loops, rotates proxy on 403/5xx, throttles on 429
- **KPI Tracking**: Comprehensive logging to Airtable KPI_Log
- **Error Handling**: Backoff + jitter on 429/5xx errors
- **Idempotent Writes**: Safe Airtable operations with upsert

## Environment Variables

```bash
# Airtable
AIRTABLE_API_KEY=your_api_key
AIRTABLE_BASE_ID=your_base_id

# Discord Webhooks
DISCORD_WEBHOOK_OPS=your_ops_webhook_url
DISCORD_WEBHOOK_ERRORS=your_errors_webhook_url

# Twilio
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_MESSAGING_SERVICE_SID=your_messaging_service_sid

# GovCon Configuration
NAICS_WHITELIST=541511,541512,541513
UEI=your_uei
CAGE_CODE=your_cage_code
SAM_SEARCH_API=https://api.sam.gov/prod/opportunities/v2/search
FPDS_ATOM_FEED=https://www.fpds.gov/ezsearch/FEEDS/ATOM?FEEDNAME=AWARD&q=

# System
ENVIRONMENT=production
PORT=8080
WATCHDOG_INTERVAL=3600
```

## Quick Start

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your credentials

# Run smoke tests
python tools/smoke.py

# Run unit tests
pytest -q

# Start the application
python main.py
```

### Docker
```bash
# Build image
docker build -t krizzy-ops .

# Run container
docker run -p 8080:8080 --env-file .env krizzy-ops
```

### Production Deployment
```bash
# Using process guard
python process_guard.py

# Or directly
python main.py
```

## API Endpoints

### Health Check
```bash
GET /health
# Returns: {"status": "ok", "ts": "2024-01-01T12:00:00Z"}
```

### Manual Triggers
```bash
# Run REI engine
POST /ops/rei

# Run GovCon engine  
POST /ops/govcon

# Run watchdog scan
POST /ops/watchdog
```

## Testing

### Smoke Tests
```bash
python tools/smoke.py
```
Tests all external integrations and returns pass/fail status.

### Unit Tests
```bash
pytest -q
```
Runs comprehensive test suite with coverage reporting.

### CI/CD
GitHub Actions workflow runs on every PR:
- Linting (Ruff + Black)
- Unit tests with coverage
- Smoke tests
- Security scanning (Bandit)
- Docker build (on main branch)

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   REI Engine    │    │  GovCon Engine   │    │    Watchdog     │
│                 │    │                  │    │                 │
│ • Zillow API    │    │ • SAM.gov API    │    │ • Health Check  │
│ • Craigslist    │    │ • FPDS Feed      │    │ • Restart Logic │
│ • Twilio SMS    │    │ • NAICS Filter   │    │ • Proxy Rotation│
└─────────┬───────┘    └─────────┬────────┘    └─────────┬───────┘
          │                      │                       │
          └──────────────────────┼───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │     Airtable API        │
                    │                         │
                    │ • Leads_REI            │
                    │ • GovCon_Opportunities │
                    │ • KPI_Log              │
                    └─────────────────────────┘
```

## Monitoring

### KPI Events
All system events are tracked in Airtable KPI_Log:
- `boot`: System startup
- `cycle_start`: Engine cycle begins
- `cycle_end`: Engine cycle completes
- `error`: System errors

### Discord Notifications
- **Ops Channel**: Success notifications and status updates
- **Errors Channel**: Error alerts and failure notifications

### Health Monitoring
- Health endpoint for uptime monitoring
- Watchdog process for automatic recovery
- Comprehensive logging throughout

## Security

- No secrets logged (uses environment variable names)
- Non-root Docker user
- Input validation and sanitization
- Rate limiting and backoff on API calls
- Content rotation for Twilio (30007 error handling)

## Performance

- Idempotent operations prevent duplicate data
- Exponential backoff with jitter for retries
- Connection pooling and timeouts
- Efficient deduplication algorithms
- Proxy rotation for high-volume requests

## Troubleshooting

### Common Issues

1. **Airtable Connection Failed**
   - Check `AIRTABLE_API_KEY` and `AIRTABLE_BASE_ID`
   - Verify API key permissions

2. **Discord Webhooks Not Working**
   - Check `DISCORD_WEBHOOK_OPS` and `DISCORD_WEBHOOK_ERRORS`
   - Verify webhook URLs are valid

3. **Twilio SMS Failed**
   - Check `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_MESSAGING_SERVICE_SID`
   - Verify account has sufficient credits

4. **SAM.gov API Errors**
   - Check `SAM_SEARCH_API` URL
   - Verify network connectivity

### Logs
Check application logs for detailed error information:
```bash
# Docker logs
docker logs <container_id>

# Local logs
tail -f logs/krizzy-ops.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run `pytest -q` and `python tools/smoke.py`
5. Submit a pull request

## License

Proprietary - KRIZZY OPS v3.0.0
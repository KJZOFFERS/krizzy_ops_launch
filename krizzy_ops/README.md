# KRIZZY OPS - Background Data Processing Service

A Python web service that runs background data processing engines for real estate investment and government contracting opportunities.

## Features

- **Real Estate Investment (REI) Engine**: Scrapes property data from configured URLs and stores in Airtable
- **Government Contracting (GovCon) Engine**: Fetches opportunities from SAM.gov API
- **Watchdog**: Provides health monitoring and heartbeat
- **Auto-Recovery**: Uses LLM to automatically fix crashed engines
- **Discord Integration**: Sends logs and errors to Discord webhook

## Architecture

```
krizzy_ops/
├── main.py                 # Main application and supervisor
├── engines/
│   ├── rei_dispo.py       # Real estate data processing
│   ├── govcon_subtrap.py  # Government contracting data
│   └── watchdog.py        # Health monitoring
├── utils/
│   ├── airtable_utils.py  # Airtable integration
│   ├── discord_utils.py   # Discord webhook integration
│   ├── proxy_utils.py     # Proxy rotation
│   └── llm_control.py     # LLM-based auto-recovery
└── requirements.txt       # Python dependencies
```

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy environment variables:
   ```bash
   cp .env.example .env
   ```

3. Configure your `.env` file with:
   - Airtable API credentials
   - Discord webhook URL
   - OpenAI API key (for auto-recovery)
   - SAM.gov API key
   - REI feed URLs
   - Proxy pool (optional)

4. Run the service:
   ```bash
   python main.py
   ```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AIRTABLE_API_KEY` | Airtable API key | Yes |
| `AIRTABLE_BASE_ID` | Airtable base ID | Yes |
| `DISCORD_WEBHOOK_OPS` | Discord webhook URL | No |
| `OPENAI_API_KEY` | OpenAI API key for auto-recovery | No |
| `SAM_API_KEY` | SAM.gov API key | No |
| `REI_FEED_URLS` | Comma-separated REI feed URLs | No |
| `NAICS_WHITELIST` | Comma-separated NAICS codes | No |
| `PROXY_ROTATE_POOL` | Comma-separated proxy URLs | No |
| `REI_INTERVAL_SEC` | REI processing interval (default: 3600) | No |
| `GOVCON_INTERVAL_SEC` | GovCon processing interval (default: 3600) | No |
| `PORT` | Server port (default: 8080) | No |

## Health Check

The service provides a health check endpoint:
```
GET /health
```

Returns: `{"status": "ok"}`

## Auto-Recovery

When an engine crashes, the system:
1. Logs the error to Discord
2. Sends the error to OpenAI for automatic code fixing
3. Reloads the fixed module
4. Continues running

## Deployment

The project includes a `Procfile` for Heroku deployment:
```
web: python main.py
```

## Notes

- All engines run in infinite loops with configurable intervals
- The watchdog sends a heartbeat every 15 minutes
- Proxy rotation is supported for web requests
- Data is upserted to Airtable to avoid duplicates
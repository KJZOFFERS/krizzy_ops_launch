# KRIZZY OPS V2 - 24/7 Autonomous REI + GovCon Engine

## Architecture

**V2 is a complete rewrite with:**
- 24/7 autonomous daemon loops (no manual triggers needed)
- Dynamic interval orchestration (speeds up/slows down based on load)
- Self-healing thread supervisor (auto-restarts crashed engines)
- Modular, Cursor-friendly structure

## Directory Structure

```
app_v2/
├── main_v2.py                    # FastAPI app + startup orchestration
├── config.py                     # All configuration constants
├── loop_orchestrator.py          # Dynamic interval controller
├── thread_supervisor.py          # Self-healing thread manager
│
├── engines/
│   ├── input_engine.py           # 24/7 Gmail + scraper ingestion
│   ├── underwriting_engine.py    # MAO/spread/strategy computation
│   ├── buyer_engine.py           # Deal-buyer matching + blasting
│   ├── outbound_control_engine.py# Twilio throttling + compliance
│   ├── buyer_performance_engine.py# Buyer tiering + predictions
│   ├── market_intel_engine.py    # ZIP-level heatmaps
│   ├── govcon_engine.py          # SAM.gov opportunity monitoring
│
├── utils/
│   ├── airtable_client.py        # Airtable CRUD operations
│   ├── gmail_client.py           # Gmail API wrapper (TODO)
│   ├── twilio_client.py          # Twilio SMS wrapper (TODO)
│   ├── discord_client.py         # Discord webhooks
│   ├── logger.py                 # Structured logging
│   ├── scoring_utils.py          # MAO, spread, buyer matching
│   ├── parsing_utils.py          # Deal payload parsing (TODO)
│
├── models/
│   ├── deal.py                   # Deal data model
│   ├── buyer.py                  # Buyer data model
│   ├── govcon.py                 # GovCon opportunity model (TODO)
│   ├── system_state.py           # Global system state tracker
│
├── requirements.txt
├── Dockerfile                    # TODO
└── .env.example                  # TODO
```

## Engines

### 1. Input Engine (TODO)
- Pulls Gmail messages with label `JV_Deals`
- Normalizes text into structured deal fields
- Validates and scores pre-underwriting
- Inserts into `Inbound_REI_Raw`

### 2. Underwriting Engine (IMPLEMENTED)
- Reads NEW deals from `Inbound_REI_Raw`
- Computes MAO, spread, spread_ratio
- Assigns strategy (FLIP/RENTAL/WHOLESALE/TRASH)
- Writes to `Leads_REI`
- Alerts on high-value deals

### 3. Buyer Engine (TODO)
- Matches deals to buyers by ZIP, price, rehab appetite
- Sends SMS + email packets
- Tracks responses

### 4. Outbound Control Engine (TODO)
- Monitors Twilio deliverability
- Rotates message templates
- Dynamic throttling based on reply rates

### 5. Buyer Performance Engine (TODO)
- Tiers buyers (A/B/C)
- Tracks closing velocity
- Predicts best buyers per ZIP

### 6. Market Intel Engine (TODO)
- Computes ZIP-level deal velocity
- Ranks ZIPs (Hot/Normal/Cold/Blacklist)
- Feeds insights to other engines

### 7. GovCon Engine (TODO)
- Monitors SAM.gov for opportunities
- Filters by NAICS + deadline
- Scores bid fit

## Dynamic Orchestration

The **Loop Orchestrator** adjusts engine intervals based on:
- Inbound lead velocity → speeds up input/underwriting
- Buyer response rates → adjusts blast frequency
- Deliverability scores → throttles outbound
- Hot ZIPs detected → prioritizes those areas
- GovCon deadlines → increases monitoring frequency

## Self-Healing

The **Thread Supervisor**:
- Monitors all engine threads
- Restarts crashed engines automatically
- Alerts via Discord on failures
- Tracks consecutive errors and escalates if critical

## Running Locally

```bash
cd app_v2
pip install -r requirements.txt

# Set environment variables
export AIRTABLE_API_KEY=...
export AIRTABLE_BASE_ID=...
export DISCORD_WEBHOOK_OPS=...
export DISCORD_WEBHOOK_ERRORS=...

# Run
python main_v2.py
```

## API Endpoints

- `GET /health` - System health + engine status
- `GET /metrics` - Detailed system metrics
- `POST /trigger/underwriting` - Manual underwriting cycle (testing only)

## Status

**Current Status: PARTIAL IMPLEMENTATION**

✅ Implemented:
- Core architecture (orchestrator, supervisor, models)
- Underwriting engine (full)
- Scoring utilities (MAO, spread, buyer matching)
- Airtable + Discord clients
- Dynamic interval control
- Self-healing threads

🚧 TODO:
- Input engine (Gmail + parsing)
- Buyer engine (matching + blasting)
- Outbound control engine
- Buyer performance engine
- Market intel engine
- GovCon engine
- Gmail client
- Twilio client
- Dockerfile
- Full integration testing

## Migration from V1

V1 (current `main.py`) uses manual trigger endpoints.
V2 runs autonomously 24/7.

**Both can run simultaneously:**
- V1 on port 8080 (Railway)
- V2 on port 8081 (local testing)

Once V2 is fully tested, replace V1 deployment.

# KRIZZY OPS v3 Enterprise Engine

Production-ready REI and GovCon automation system with zero cracks.

## 🚀 Features

### REI Disposition Engine
- **Multi-source lead aggregation** from Zillow RSS, Craigslist, Realtor.com, and FSBO.com
- **Intelligent deduplication** using SHA-256 hashing of source URLs and contact info
- **Lead scoring and qualification** based on contact availability and property details
- **Automated SMS outreach** via Twilio MessagingService with content rotation
- **PII protection** with hashed phone/email storage

### GovCon Subtrap Engine
- **SAM.gov API integration** with Combined Synopsis/Solicitation filtering
- **FPDS ATOM feed processing** for comprehensive opportunity coverage
- **NAICS whitelist filtering** for targeted opportunity matching
- **Due date proximity filtering** (within 7 days)
- **Comprehensive bid pack generation** with officer contact details
- **Automated outreach** to high-scoring opportunities

### Infrastructure
- **Production-grade error handling** with exponential backoff and jitter
- **Comprehensive KPI tracking** with Airtable integration
- **Discord notifications** for ops and error channels
- **Health monitoring** with `/health` endpoint
- **Watchdog system** with process monitoring and proxy rotation
- **Rate limiting protection** with automatic throttling

## 📋 Requirements

- Python 3.11+
- Airtable account with API access
- Discord webhooks for notifications
- Twilio account with MessagingService
- Environment variables (see `.env.example`)

## 🛠️ Installation

1. **Clone and install dependencies:**
```bash
git clone <repository>
cd krizzy-ops
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your actual credentials
```

3. **Run tests:**
```bash
pytest -q
```

4. **Run smoke tests:**
```bash
python tools/smoke.py
```

5. **Start the application:**
```bash
python main.py
```

## 🔧 Configuration

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `AIRTABLE_API_KEY` | Airtable API key |
| `AIRTABLE_BASE_ID` | Airtable base ID |
| `DISCORD_WEBHOOK_OPS` | Discord webhook for operations |
| `DISCORD_WEBHOOK_ERRORS` | Discord webhook for errors |
| `TWILIO_ACCOUNT_SID` | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `TWILIO_MESSAGING_SERVICE_SID` | Twilio messaging service SID |
| `NAICS_WHITELIST` | Comma-separated NAICS codes |
| `UEI` | Unique Entity Identifier |
| `CAGE_CODE` | Commercial and Government Entity code |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Application port | `8080` |
| `PROXY_LIST` | Comma-separated proxy list | None |
| `FPDS_ATOM_FEED` | FPDS feed URL | Default FPDS URL |
| `SAM_SEARCH_API` | SAM.gov API URL | Default SAM URL |

## 🏗️ Architecture

### Core Components

1. **Main Application** (`main.py`)
   - Flask web server with health endpoint
   - KPI logging on every boot and cycle
   - Comprehensive error handling

2. **REI Engine** (`rei_dispo_engine.py`)
   - RSS feed parsing and lead extraction
   - Data enrichment and validation
   - Automated SMS outreach

3. **GovCon Engine** (`govcon_subtrap_engine.py`)
   - SAM.gov and FPDS integration
   - Multi-stage filtering pipeline
   - Bid pack generation

4. **Utilities**
   - `airtable_utils.py`: Safe database operations with upsert logic
   - `discord_utils.py`: Notification system with backoff
   - `twilio_utils.py`: SMS operations with content rotation
   - `watchdog.py`: System monitoring and recovery

### Data Flow

```
External Sources → Engines → Validation → Deduplication → Airtable → Outreach
                     ↓
                 KPI Logging → Discord Notifications
```

## 🧪 Testing

### Unit Tests
```bash
pytest -v
```

### Smoke Tests
```bash
python tools/smoke.py
```

### Linting and Formatting
```bash
ruff check . --fix
black .
```

## 🚀 Deployment

### Railway/Heroku
1. Set environment variables in platform dashboard
2. Deploy from Git repository
3. Verify health endpoint: `curl https://your-app.com/health`

### Docker
```bash
docker build -t krizzy-ops .
docker run -p 8080:8080 --env-file .env krizzy-ops
```

## 📊 API Endpoints

### Health Check
```
GET /health
Response: {"status": "ok", "ts": "2024-01-01T00:00:00", "service": "KRIZZY-OPS-v3"}
```

### Engine Triggers
```
POST /ops/rei        # Trigger REI engine
POST /ops/govcon     # Trigger GovCon engine  
POST /ops/watchdog   # Trigger watchdog scan
```

## 📈 Monitoring

### KPI Tracking
- Boot events with timestamps
- Cycle start/end with duration
- Error events with context
- Message sending statistics

### Discord Notifications
- ✅ Operations channel: Successful cycles, system status
- ❌ Errors channel: Failures, exceptions, rate limits

### Health Monitoring
- `/health` endpoint for uptime checks
- Process monitoring via watchdog
- Automatic restart on failures

## 🔒 Security

- **PII Protection**: Phone/email hashing in dedup keys
- **Rate Limiting**: Automatic backoff on 429/5xx errors
- **Input Validation**: Comprehensive data sanitization
- **Error Handling**: No sensitive data in logs
- **Proxy Rotation**: IP rotation on 403/5xx responses

## 📝 Compliance

- **HARD RULES COMPLIANCE**:
  - ✅ No placeholders or TODOs
  - ✅ Python 3.11 with Ruff + Black
  - ✅ Environment variable names exactly as specified
  - ✅ No secrets in logs
  - ✅ All writes idempotent with backoff + jitter
  - ✅ KPI push on every boot and cycle

## 🤝 Contributing

1. Follow the existing code style (Ruff + Black)
2. Add tests for new functionality
3. Update documentation
4. Ensure smoke tests pass

## 📄 License

MIT License - see LICENSE file for details.

---

**KRIZZY OPS v3** - Production-ready with zero cracks. 🚀
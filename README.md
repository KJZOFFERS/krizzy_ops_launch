# KRIZZY OPS v3.0.0

Production-ready automation system for Real Estate Investment (REI) and Government Contracting (GovCon) operations.

## 🚀 Features

### REI Disposition Engine
- **Multi-source data collection**: Zillow, Craigslist, Realtor.com
- **Lead enrichment**: Contact validation, scoring, deduplication
- **Airtable integration**: Safe writes with upsert logic
- **Twilio messaging**: SMS notifications to buyers with content rotation
- **Discord notifications**: Real-time operations updates

### GovCon Subtrap Engine
- **SAM.gov integration**: Automated opportunity discovery
- **FPDS ATOM feed**: Contract data enrichment
- **Smart filtering**: NAICS whitelist, due date windows, solicitation types
- **Bid pack generation**: Structured JSON for proposal preparation
- **Compliance tracking**: UEI, CAGE code management

### Production Infrastructure
- **Health monitoring**: `/health` endpoint with uptime tracking
- **Process guard**: Automatic restart with exponential backoff
- **KPI logging**: Comprehensive metrics and alerting
- **Error handling**: Retry logic with jitter for all external APIs
- **Security**: No secrets in logs, environment-based configuration

## 🛠️ Installation

### Prerequisites
- Python 3.11+
- Airtable account with API key
- Twilio account with Messaging Service
- Discord webhooks for notifications
- SAM.gov API access

### Environment Variables

```bash
# Airtable
AIRTABLE_API_KEY=your_airtable_api_key
AIRTABLE_BASE_ID=your_base_id

# Discord
DISCORD_WEBHOOK_OPS=https://discord.com/api/webhooks/ops_webhook
DISCORD_WEBHOOK_ERRORS=https://discord.com/api/webhooks/errors_webhook

# Twilio
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_MESSAGING_SERVICE_SID=your_messaging_service_sid
TWILIO_SAFE_MODE=false  # Set to true for testing

# SAM.gov
SAM_SEARCH_API=https://api.sam.gov/v1/search
SAM_API_KEY=your_sam_api_key
NAICS_WHITELIST=541511,541512,541519
UEI=your_uei
CAGE_CODE=your_cage_code

# FPDS
FPDS_ATOM_FEED=https://www.fpds.gov/fpdsng_cms/index.php/reports

# Application
PORT=8080
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### Installation

```bash
# Clone repository
git clone <repository-url>
cd krizzy-ops

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Start application
python main.py

# Or use process guard for production
python process_guard.py
```

## 📊 API Endpoints

### Health Check
```bash
GET /health
```
Returns system status and uptime information.

### REI Operations
```bash
POST /ops/rei
```
Runs REI lead collection and processing cycle.

### GovCon Operations
```bash
POST /ops/govcon
```
Runs government contracting opportunity discovery cycle.

### Watchdog
```bash
POST /ops/watchdog
```
Runs data integrity scan and process monitoring.

## 🧪 Testing

### Unit Tests
```bash
pytest test_*.py -v
```

### Integration Tests
```bash
pytest -m integration -v
```

### Smoke Tests
```bash
python tools/smoke.py
```

### Coverage Report
```bash
pytest --cov=. --cov-report=html
```

## 🔧 Development

### Code Quality
```bash
# Format code
black .

# Lint code
ruff check .

# Type checking
mypy .
```

### Pre-commit Hooks
```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install
```

## 🚀 Deployment

### Docker
```bash
# Build image
docker build -t krizzy-ops:latest .

# Run container
docker run -d \
  --name krizzy-ops \
  -p 8080:8080 \
  --env-file .env \
  krizzy-ops:latest
```

### Railway
```bash
# Deploy to Railway
railway login
railway link
railway up
```

### Manual Deployment
```bash
# Install dependencies
pip install -r requirements.txt

# Run with process guard
python process_guard.py
```

## 📈 Monitoring

### Health Checks
- **Endpoint**: `GET /health`
- **Response**: `{"status": "ok", "ts": "2024-01-01T00:00:00Z", "uptime_seconds": 3600}`

### KPI Tracking
All operations are logged to Airtable `KPI_Log` table with:
- Event type (boot, cycle_start, cycle_end, error)
- Timestamp
- Performance metrics
- Error details

### Discord Notifications
- **Operations**: Real-time cycle updates
- **Errors**: Critical error alerts
- **Status**: System health notifications

## 🔒 Security

### Environment Variables
- All secrets stored in environment variables
- No hardcoded credentials
- Secure logging (secrets filtered from logs)

### API Security
- Rate limiting with exponential backoff
- Request timeout handling
- Error message sanitization

### Data Protection
- Contact information hashing for deduplication
- Secure Airtable API key management
- Twilio safe mode for testing

## 📋 Airtable Schema

### Leads_REI Table
- Address, City, State, Zip
- Price, ARV, Agent info
- Phone, Email, Source_URL
- Source, Timestamp, lead_score
- source_id, contact_hash (deduplication)

### GovCon_Opportunities Table
- Solicitation #, Title, NAICS
- Due_Date, Days_Until_Due
- Officer, Email, Phone
- Agency, Sub_Agency, Status
- Link, Description, Estimated_Value
- Bid_Pack_JSON, Source, source_id

### KPI_Log Table
- Event, Timestamp, Data
- Status, System, Version
- Engine, Records_Processed
- Error_Type, Error_Message

### Buyers Table
- Name, Phone, Email
- Preferences, Status
- Last_Contact, Notes

## 🐛 Troubleshooting

### Common Issues

1. **Airtable Rate Limits**
   - System automatically retries with exponential backoff
   - Check API key permissions
   - Verify base ID is correct

2. **Twilio 30007 Error**
   - Content rotation is automatic
   - Check messaging service configuration
   - Verify phone number format

3. **SAM.gov API Issues**
   - Verify API key is valid
   - Check NAICS whitelist format
   - Ensure UEI and CAGE code are correct

4. **Discord Webhook Failures**
   - Verify webhook URLs are correct
   - Check webhook permissions
   - Test with curl

### Logs
- Application logs: `logs/krizzy_ops.log`
- Error logs: `logs/errors.log`
- Log rotation: 10MB max, 5 backups

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python main.py
```

## 📞 Support

For issues and questions:
1. Check the logs first
2. Run smoke tests: `python tools/smoke.py`
3. Review environment variables
4. Check external service status

## 📄 License

MIT License - see LICENSE file for details.

## 🔄 Version History

### v3.0.0 (Current)
- Production-ready architecture
- Comprehensive error handling
- KPI tracking and monitoring
- Automated testing and CI/CD
- Docker containerization
- Process guard with restart logic

### v2.x (Legacy)
- Basic functionality
- Limited error handling
- Manual operations

---

**KRIZZY OPS v3.0.0** - Zero cracks, production ready. 🚀
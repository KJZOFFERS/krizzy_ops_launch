# KRIZZY OPS DEPLOYMENT GUIDE

## FILES CREATED

All files are ready in `/mnt/user-data/outputs/`:

```
outputs/
├── main.py                      ← NEW: Web endpoint for Railway
├── Procfile                     ← UPDATED: Added web process
├── requirements.txt             ← UPDATED: Added fastapi + uvicorn
└── src/
    ├── ops_health_service.py    ← MOVED: From src/common/
    ├── govcon_subtrap_engine.py ← MOVED: From src/common/
    └── rei_dispo_engine.py      ← MOVED: From src/common/
```

## DEPLOYMENT STEPS

### Step 1: Download all files from outputs folder

Click the download links above for each file.

### Step 2: Replace files in your repo

```bash
# In your krizzy_ops_launch repo:

# Replace root files
cp ~/Downloads/main.py .
cp ~/Downloads/Procfile .
cp ~/Downloads/requirements.txt .

# Replace service files (IMPORTANT: these go in src/, NOT src/common/)
cp ~/Downloads/ops_health_service.py src/
cp ~/Downloads/govcon_subtrap_engine.py src/
cp ~/Downloads/rei_dispo_engine.py src/

# Delete old files from src/common/ (if they exist)
rm src/common/ops_health_service.py 2>/dev/null
rm src/common/govcon_subtrap_engine.py 2>/dev/null
rm src/common/rei_dispo_engine.py 2>/dev/null
```

### Step 3: Commit and push

```bash
git add .
git commit -m "Fix: Add web process + move services to src/ root"
git push origin main
```

### Step 4: Verify deployment

After Railway redeploys, check logs for:

```
[web] INFO:     Uvicorn running on http://0.0.0.0:8080
[ops_health] [OPS_HEALTH] Starting service...
[govcon] [GOVCON] Starting service...
[rei_dispo] [REI] Starting service...
```

### Step 5: Test the endpoint

```bash
curl https://krizzy-ops-launch.vercel.app/health
# Should return: {"status":"healthy"}
```

## WHAT WAS FIXED

1. ✅ Added `fastapi` and `uvicorn` to requirements.txt
2. ✅ Created `main.py` with minimal web endpoint
3. ✅ Updated Procfile with `web:` process
4. ✅ Moved service files from `src/common/` to `src/` (Procfile compatibility)
5. ✅ Fixed all imports in service files

## EXPECTED RESULT

- **No more "uvicorn: command not found" errors**
- **No more "gunicorn: command not found" errors**
- **All 4 processes running**: web + 3 workers
- **Railway health checks passing**

## TROUBLESHOOTING

If still seeing errors:

1. Check Railway is using Python 3.11+
2. Force rebuild: Add a comment to main.py and push again
3. Check Railway environment variables are set correctly
4. Verify src/common/ directory still exists with the helper modules

## ENVIRONMENT VARIABLES REQUIRED

Make sure these are set in Railway:

```
AIRTABLE_API_KEY=your_key
AIRTABLE_BASE_ID=your_base
DISCORD_WEBHOOK_OPS=your_webhook
DISCORD_WEBHOOK_ERRORS=your_webhook
RUN_INTERVAL_MINUTES=60
```

Optional:
```
SAM_SEARCH_API=
FPDS_ATOM_FEED=
NAICS_WHITELIST=
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_MESSAGING_SERVICE_SID=
```

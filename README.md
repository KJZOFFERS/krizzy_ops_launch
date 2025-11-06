# Krizzy Ops (Offline-capable)
- When internet is available: runs FastAPI + Prometheus at /health, /metrics, /command (POST).
- When offline: `python main.py` starts a stdlib HTTP server exposing the same routes (minimal metrics).
Offline verify:
make verify_offline
python main.py  # then hit /health and /command with any HTTP client
Deploy (online): use Docker/ Railway; requirements.txt will install then.

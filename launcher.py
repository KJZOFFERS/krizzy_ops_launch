"""
KRIZZY OPS UNIFIED LAUNCHER
Runs web server + all 3 worker engines in a single Railway process
"""
import os
import sys
import threading
import time
from datetime import datetime

# Import the web app
from main import app

# Import worker engines
from src import ops_health_service, govcon_subtrap_engine, rei_dispo_engine


def run_worker(name: str, module):
    """Run a worker module's main() in a thread"""
    print(f"[LAUNCHER] Starting {name} worker thread...")
    try:
        module.main()
    except Exception as e:
        print(f"[LAUNCHER] ERROR in {name}: {e}")
        time.sleep(60)


def main():
    """Start web server + all workers"""
    print(f"[LAUNCHER] KRIZZY OPS starting at {datetime.now().isoformat()}")
    print(f"[LAUNCHER] Python version: {sys.version}")
    print(f"[LAUNCHER] Starting 3 worker threads + web server...")
    
    # Start worker threads
    workers = [
        ("OPS_HEALTH", ops_health_service),
        ("GOVCON", govcon_subtrap_engine),
        ("REI_DISPO", rei_dispo_engine),
    ]
    
    threads = []
    for name, module in workers:
        t = threading.Thread(target=run_worker, args=(name, module), daemon=True)
        t.start()
        threads.append((name, t))
        print(f"[LAUNCHER] ✅ {name} thread started")
    
    # Give threads a moment to initialize
    time.sleep(2)
    
    # Start web server (blocking call)
    print(f"[LAUNCHER] Starting web server on port {os.getenv('PORT', 8080)}...")
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        log_level="info"
    )


if __name__ == "__main__":
    main()

# launcher.py

import sys
import os
import time
import threading
import logging
from datetime import datetime

# Add src to path if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
from src.rei_dispo_engine import main as rei_main
from src.govcon_subtrap_engine import main as govcon_main
from src.ops_health_service import main as health_main
from src.ops import run_preflight


def run_worker(worker_func, name: str):
    """Run a worker function in a loop"""
    while True:
        try:
            worker_func()
        except Exception as e:
            print(f"[{name}] Worker error: {e}")
            time.sleep(60)


def main():
    """Main entry point - starts all worker threads + web server"""
    print(f"[LAUNCHER] KRIZZY OPS starting at {datetime.now().isoformat()}")
    print(f"[LAUNCHER] Python version: {sys.version}")
    
    # Run preflight checks
    print("[LAUNCHER] Running preflight checks...")
    preflight_ok = run_preflight()
    
    if not preflight_ok:
        print("[LAUNCHER] WARNING: PREFLIGHT FAILED - continuing in degraded mode")
    
    print("[LAUNCHER] Starting 3 worker threads + web server...")
    
    # Start worker threads
    print("[LAUNCHER] Starting OPS_HEALTH worker thread...")
    health_thread = threading.Thread(
        target=run_worker,
        args=(health_main, "OPS_HEALTH"),
        daemon=True,
        name="OPS_HEALTH_SERVICE"
    )
    health_thread.start()
    print("[LAUNCHER] OPS_HEALTH thread started")
    
    print("[LAUNCHER] Starting GOVCON worker thread...")
    govcon_thread = threading.Thread(
        target=run_worker,
        args=(govcon_main, "GOVCON"),
        daemon=True,
        name="GOVCON_SUBTRAP_ENGINE"
    )
    govcon_thread.start()
    print("[LAUNCHER] GOVCON thread started")
    
    print("[LAUNCHER] Starting REI_DISPO worker thread...")
    rei_thread = threading.Thread(
        target=run_worker,
        args=(rei_main, "REI_DISPO"),
        daemon=True,
        name="REI_DISPO_ENGINE"
    )
    rei_thread.start()
    print("[LAUNCHER] REI_DISPO thread started")
    
    # Small delay to let threads initialize
    time.sleep(1)
    
    # Start web server (blocking call)
    print("[LAUNCHER] Starting web server on port 8080...")
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8080")),
        log_level="info"
    )


if __name__ == "__main__":
    main()

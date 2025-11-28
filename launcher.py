# launcher.py

"""
KRIZZY OPS UNIFIED LAUNCHER
Runs web server + all 3 worker engines in a single Railway process
@@ -8,6 +10,9 @@
import time
from datetime import datetime

# Import preflight
from src.ops import run_preflight

# Import the web app
from main import app

@@ -29,6 +34,15 @@ def main():
    """Start web server + all workers"""
    print(f"[LAUNCHER] KRIZZY OPS starting at {datetime.now().isoformat()}")
    print(f"[LAUNCHER] Python version: {sys.version}")
    
    # Run preflight checks
    print("[LAUNCHER] Running preflight checks...")
    preflight_ok = run_preflight()
    
    if not preflight_ok:
        print("[LAUNCHER] ⚠️  PREFLIGHT FAILED - some systems degraded but continuing...")
        # Don't exit, just warn - let engines handle their own errors
    
    print(f"[LAUNCHER] Starting 3 worker threads + web server...")

    # Start worker threads

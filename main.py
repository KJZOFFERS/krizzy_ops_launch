"""
KRIZZY OPS v3.0.0 - Production-ready Flask application.
"""
from flask import Flask, jsonify
from rei_dispo_engine import run_rei
from govcon_subtrap_engine import run_govcon
from watchdog import run_watchdog
from kpi import kpi_push
import datetime
import os
import time


app = Flask(__name__)

# Track startup time for health checks
startup_time = time.time()


@app.route("/ops/rei", methods=["POST"])
def rei():
    """Run REI data pull and log results to Airtable."""
    try:
        kpi_push("cycle_start", {"engine": "rei"})
        count = run_rei()
        kpi_push("cycle_end", {"engine": "rei", "count": count})
        return jsonify({"REI_Leads": count, "status": "success"})
    except Exception as e:
        kpi_push("error", {
            "error_type": "rei_cycle_error",
            "message": str(e),
            "engine": "rei"
        })
        return jsonify({"error": str(e), "status": "error"}), 500


@app.route("/ops/govcon", methods=["POST"])
def govcon():
    """Run GovCon data pull and log results to Airtable."""
    try:
        kpi_push("cycle_start", {"engine": "govcon"})
        count = run_govcon()
        kpi_push("cycle_end", {"engine": "govcon", "count": count})
        return jsonify({"GovCon_Bids": count, "status": "success"})
    except Exception as e:
        kpi_push("error", {
            "error_type": "govcon_cycle_error",
            "message": str(e),
            "engine": "govcon"
        })
        return jsonify({"error": str(e), "status": "error"}), 500


@app.route("/ops/watchdog", methods=["POST"])
def watch():
    """Run daily data integrity scan."""
    try:
        kpi_push("cycle_start", {"engine": "watchdog"})
        count = run_watchdog()
        kpi_push("cycle_end", {"engine": "watchdog", "count": count})
        return jsonify({"Cleaned": count, "status": "success"})
    except Exception as e:
        kpi_push("error", {
            "error_type": "watchdog_cycle_error",
            "message": str(e),
            "engine": "watchdog"
        })
        return jsonify({"error": str(e), "status": "error"}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health endpoint with timestamp for uptime monitoring."""
    uptime = time.time() - startup_time
    return jsonify({
        "status": "ok",
        "ts": datetime.datetime.utcnow().isoformat(),
        "uptime_seconds": round(uptime, 2),
        "version": "3.0.0"
    })


# --- Main entry point for Railway ---
if __name__ == "__main__":
    # Log startup
    kpi_push("boot", {
        "version": "3.0.0",
        "environment": os.getenv("ENVIRONMENT", "production"),
        "port": os.getenv("PORT", "8080")
    })
    
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)

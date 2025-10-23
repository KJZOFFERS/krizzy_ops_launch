from flask import Flask, jsonify
from rei_dispo_engine import run_rei
from govcon_subtrap_engine import run_govcon
from watchdog import run_watchdog
from kpi import track_cycle_start, track_cycle_end, track_error, track_boot
import datetime
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route("/ops/rei", methods=["POST"])
def rei():
    """Run REI data pull and log results to Airtable."""
    try:
        track_cycle_start("REI")
        count = run_rei()
        track_cycle_end("REI", count, success=True)
        return jsonify({"REI_Leads": count, "status": "success"})
    except Exception as e:
        track_error("REI", str(e))
        logger.error(f"REI cycle failed: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500


@app.route("/ops/govcon", methods=["POST"])
def govcon():
    """Run GovCon data pull and log results to Airtable."""
    try:
        track_cycle_start("GovCon")
        count = run_govcon()
        track_cycle_end("GovCon", count, success=True)
        return jsonify({"GovCon_Bids": count, "status": "success"})
    except Exception as e:
        track_error("GovCon", str(e))
        logger.error(f"GovCon cycle failed: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500


@app.route("/ops/watchdog", methods=["POST"])
def watch():
    """Run daily data integrity scan."""
    try:
        track_cycle_start("Watchdog")
        count = run_watchdog()
        track_cycle_end("Watchdog", count, success=True)
        return jsonify({"Cleaned": count, "status": "success"})
    except Exception as e:
        track_error("Watchdog", str(e))
        logger.error(f"Watchdog cycle failed: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health endpoint for Railway uptime check."""
    try:
        # Basic health check
        health_data = {
            "status": "ok",
            "ts": datetime.datetime.utcnow().isoformat(),
            "version": "3.0.0",
            "environment": os.getenv("ENVIRONMENT", "production")
        }
        
        # Check critical environment variables
        required_env_vars = [
            "AIRTABLE_API_KEY", "AIRTABLE_BASE_ID",
            "DISCORD_WEBHOOK_OPS", "DISCORD_WEBHOOK_ERRORS",
            "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_MESSAGING_SERVICE_SID"
        ]
        
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            health_data["warnings"] = f"Missing env vars: {', '.join(missing_vars)}"
        
        return jsonify(health_data)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "error",
            "ts": datetime.datetime.utcnow().isoformat(),
            "error": str(e)
        }), 500


# --- Main entry point for Railway ---
if __name__ == "__main__":
    # Track boot event
    track_boot()
    
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting KRIZZY OPS v3.0.0 on port {port}")
    app.run(host="0.0.0.0", port=port)

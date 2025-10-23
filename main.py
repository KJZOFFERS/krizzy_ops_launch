import logging
import os
from datetime import datetime

from flask import Flask, jsonify

from airtable_utils import kpi_push
from discord_utils import post_error, post_ops
from govcon_subtrap_engine import run_govcon
from rei_dispo_engine import run_rei
from watchdog import run_watchdog

# Configure logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Boot KPI
kpi_push(
    "boot",
    {
        "status": "starting",
        "timestamp": datetime.utcnow().isoformat(),
        "port": os.environ.get("PORT", 8080),
    },
)
post_ops("KRIZZY OPS v3 Enterprise Engine starting up...")


@app.route("/health", methods=["GET"])
def health():
    """Health endpoint with proper timestamp."""
    return jsonify(
        {"status": "ok", "ts": datetime.utcnow().isoformat(), "service": "KRIZZY-OPS-v3"}
    )


@app.route("/ops/rei", methods=["POST"])
def rei():
    """Run REI data pull and log results."""
    cycle_start = datetime.utcnow()
    kpi_push("cycle_start", {"engine": "REI", "timestamp": cycle_start.isoformat()})

    try:
        logger.info("Starting REI engine cycle")
        count = run_rei()

        cycle_end = datetime.utcnow()
        duration = (cycle_end - cycle_start).total_seconds()

        kpi_push(
            "cycle_end",
            {
                "engine": "REI",
                "count": count,
                "duration_seconds": duration,
                "status": "success",
                "timestamp": cycle_end.isoformat(),
            },
        )

        post_ops(f"REI cycle completed: {count} leads processed in {duration:.1f}s")
        return jsonify({"REI_Leads": count, "duration": duration})

    except Exception as e:
        cycle_end = datetime.utcnow()
        duration = (cycle_end - cycle_start).total_seconds()

        logger.error(f"REI engine failed: {e}")
        kpi_push(
            "error",
            {
                "engine": "REI",
                "error": str(e),
                "duration_seconds": duration,
                "timestamp": cycle_end.isoformat(),
            },
        )

        post_error(f"REI engine failed after {duration:.1f}s: {str(e)}")
        return jsonify({"error": str(e), "duration": duration}), 500


@app.route("/ops/govcon", methods=["POST"])
def govcon():
    """Run GovCon data pull and log results."""
    cycle_start = datetime.utcnow()
    kpi_push("cycle_start", {"engine": "GovCon", "timestamp": cycle_start.isoformat()})

    try:
        logger.info("Starting GovCon engine cycle")
        count = run_govcon()

        cycle_end = datetime.utcnow()
        duration = (cycle_end - cycle_start).total_seconds()

        kpi_push(
            "cycle_end",
            {
                "engine": "GovCon",
                "count": count,
                "duration_seconds": duration,
                "status": "success",
                "timestamp": cycle_end.isoformat(),
            },
        )

        post_ops(f"GovCon cycle completed: {count} opportunities processed in {duration:.1f}s")
        return jsonify({"GovCon_Bids": count, "duration": duration})

    except Exception as e:
        cycle_end = datetime.utcnow()
        duration = (cycle_end - cycle_start).total_seconds()

        logger.error(f"GovCon engine failed: {e}")
        kpi_push(
            "error",
            {
                "engine": "GovCon",
                "error": str(e),
                "duration_seconds": duration,
                "timestamp": cycle_end.isoformat(),
            },
        )

        post_error(f"GovCon engine failed after {duration:.1f}s: {str(e)}")
        return jsonify({"error": str(e), "duration": duration}), 500


@app.route("/ops/watchdog", methods=["POST"])
def watch():
    """Run daily data integrity scan."""
    cycle_start = datetime.utcnow()
    kpi_push("cycle_start", {"engine": "Watchdog", "timestamp": cycle_start.isoformat()})

    try:
        logger.info("Starting Watchdog cycle")
        count = run_watchdog()

        cycle_end = datetime.utcnow()
        duration = (cycle_end - cycle_start).total_seconds()

        kpi_push(
            "cycle_end",
            {
                "engine": "Watchdog",
                "count": count,
                "duration_seconds": duration,
                "status": "success",
                "timestamp": cycle_end.isoformat(),
            },
        )

        post_ops(f"Watchdog cycle completed: {count} issues cleaned in {duration:.1f}s")
        return jsonify({"Cleaned": count, "duration": duration})

    except Exception as e:
        cycle_end = datetime.utcnow()
        duration = (cycle_end - cycle_start).total_seconds()

        logger.error(f"Watchdog failed: {e}")
        kpi_push(
            "error",
            {
                "engine": "Watchdog",
                "error": str(e),
                "duration_seconds": duration,
                "timestamp": cycle_end.isoformat(),
            },
        )

        post_error(f"Watchdog failed after {duration:.1f}s: {str(e)}")
        return jsonify({"error": str(e), "duration": duration}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500


# --- Main entry point ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))

    # Final boot KPI
    kpi_push("boot", {"status": "ready", "port": port, "timestamp": datetime.utcnow().isoformat()})
    post_ops(f"KRIZZY OPS v3 ready on port {port}")

    logger.info(f"Starting KRIZZY OPS on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)

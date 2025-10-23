"""Main Flask application for KRIZZY OPS."""

import os
import datetime
from flask import Flask, jsonify
from rei_dispo_engine import run_rei
from govcon_subtrap_engine import run_govcon
from watchdog import run_watchdog
from discord_utils import post_ops, post_err
import kpi


app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    """Health endpoint for uptime monitoring."""
    return jsonify({
        "status": "ok",
        "ts": datetime.datetime.utcnow().isoformat(),
    })


@app.route("/ops/rei", methods=["POST"])
def rei():
    """Run REI disposition engine."""
    try:
        count = run_rei()
        return jsonify({"REI_Leads": count})
    except Exception as e:
        post_err(f"REI endpoint error: {e}")
        kpi.kpi_push("error", {"endpoint": "rei", "error": str(e)})
        return jsonify({"error": "Internal server error"}), 500


@app.route("/ops/govcon", methods=["POST"])
def govcon():
    """Run GovCon opportunity engine."""
    try:
        count = run_govcon()
        return jsonify({"GovCon_Opportunities": count})
    except Exception as e:
        post_err(f"GovCon endpoint error: {e}")
        kpi.kpi_push("error", {"endpoint": "govcon", "error": str(e)})
        return jsonify({"error": "Internal server error"}), 500


@app.route("/ops/watchdog", methods=["POST"])
def watchdog_endpoint():
    """Run watchdog validation cycle."""
    try:
        count = run_watchdog()
        return jsonify({"Invalid_Records": count})
    except Exception as e:
        post_err(f"Watchdog endpoint error: {e}")
        kpi.kpi_push("error", {"endpoint": "watchdog", "error": str(e)})
        return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))

    kpi.kpi_push("boot", {
        "port": port,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    })
    post_ops(f"KRIZZY OPS started on port {port}")

    app.run(host="0.0.0.0", port=port)

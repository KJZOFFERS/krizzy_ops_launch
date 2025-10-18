from flask import Flask, jsonify
from rei_dispo_engine import run_rei
from govcon_subtrap_engine import run_govcon
from watchdog import run_watchdog
from airtable_utils import add_record
import datetime
import os

app = Flask(__name__)

@app.route("/ops/rei", methods=["POST"])
def rei():
    """Run REI data pull and log results to Airtable."""
    try:
        count = run_rei()
        add_record(
            "KPI_Log",
            {
                "Cycle": "REI",
                "Leads_Added": count,
                "Timestamp": datetime.datetime.utcnow().isoformat(),
            },
        )
        return jsonify({"REI_Leads": count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/ops/govcon", methods=["POST"])
def govcon():
    """Run GovCon data pull and log results to Airtable."""
    try:
        count = run_govcon()
        add_record(
            "KPI_Log",
            {
                "Cycle": "GovCon",
                "Bids_Added": count,
                "Timestamp": datetime.datetime.utcnow().isoformat(),
            },
        )
        return jsonify({"GovCon_Bids": count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/ops/watchdog", methods=["POST"])
def watch():
    """Run daily data integrity scan."""
    try:
        count = run_watchdog()
        add_record(
            "KPI_Log",
            {
                "Cycle": "Watchdog",
                "Leads_Added": count,
                "Timestamp": datetime.datetime.utcnow().isoformat(),
            },
        )
        return jsonify({"Cleaned": count})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health endpoint for Railway uptime check."""
    return jsonify({"status": "OK"})


# --- Main entry point for Railway ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

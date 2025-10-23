from flask import Flask, jsonify
from rei_dispo_engine import run_rei
from govcon_subtrap_engine import run_govcon
from watchdog import run_watchdog
from kpi import kpi_push
import datetime
import os

app = Flask(__name__)

@app.route("/ops/rei", methods=["POST"])
def rei():
    """Run REI data pull and log results to Airtable."""
    try:
        kpi_push("cycle_start", {"engine": "REI"})
        count = run_rei()
        kpi_push("cycle_end", {"engine": "REI", "leads_added": count})
        return jsonify({"REI_Leads": count})
    except Exception as e:
        kpi_push("errors", {"engine": "REI", "error": str(e)})
        return jsonify({"error": str(e)}), 500


@app.route("/ops/govcon", methods=["POST"])
def govcon():
    """Run GovCon data pull and log results to Airtable."""
    try:
        kpi_push("cycle_start", {"engine": "GOVCON"})
        count = run_govcon()
        kpi_push("cycle_end", {"engine": "GOVCON", "bids_added": count})
        return jsonify({"GovCon_Bids": count})
    except Exception as e:
        kpi_push("errors", {"engine": "GOVCON", "error": str(e)})
        return jsonify({"error": str(e)}), 500


@app.route("/ops/watchdog", methods=["POST"])
def watch():
    """Run watchdog orchestration for loops and throttling."""
    try:
        kpi_push("cycle_start", {"engine": "WATCHDOG"})
        result = run_watchdog()
        kpi_push("cycle_end", {"engine": "WATCHDOG", "result": result})
        return jsonify({"result": result})
    except Exception as e:
        kpi_push("errors", {"engine": "WATCHDOG", "error": str(e)})
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health endpoint for uptime check."""
    return jsonify({"status": "ok", "ts": datetime.datetime.utcnow().isoformat()})


# --- Main entry point for Railway ---
if __name__ == "__main__":
    # KPI on boot
    try:
        kpi_push("boot", {"workers": int(os.environ.get("WEB_CONCURRENCY", "1"))})
    except Exception:
        # Avoid hard fail on KPI write
        pass
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

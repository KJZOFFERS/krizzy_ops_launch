from flask import Flask, jsonify
from rei_dispo_engine import run_rei
from govcon_subtrap_engine import run_govcon
from watchdog import run_watchdog
from airtable_utils import add_record
import datetime

app = Flask(__name__)

@app.route("/ops/rei", methods=["POST"])
def rei():
    c = run_rei()
    add_record("KPI_Log", {"Cycle": "REI", "Leads_Added": c, "Timestamp": str(datetime.datetime.utcnow())})
    return jsonify({"REI_Leads": c})

@app.route("/ops/govcon", methods=["POST"])
def govcon():
    c = run_govcon()
    add_record("KPI_Log", {"Cycle": "GovCon", "Bids_Added": c, "Timestamp": str(datetime.datetime.utcnow())})
    return jsonify({"GovCon_Bids": c})

@app.route("/ops/watchdog", methods=["POST"])
def watch():
    c = run_watchdog()
    add_record("KPI_Log", {"Cycle": "Watchdog", "Leads_Added": c, "Timestamp": str(datetime.datetime.utcnow())})
    return jsonify({"Cleaned": c})

@app.route("/health")
def health():
    return jsonify({"status": "OK"})

import os, time, threading
from flask import Flask, jsonify
from validate_env import validate_env
from watchdog import start_watchdog
from rei_dispo_engine import start_rei_dispo
from govcon_subtrap_engine import start_govcon
from kpi import kpi_push

app = Flask(__name__)

@app.route("/health")
def health():
    return jsonify({"status": "ok", "ts": int(time.time())})

def on_startup():
    validate_env([
        "AIRTABLE_API_KEY","AIRTABLE_BASE_ID",
        "DISCORD_WEBHOOK_OPS","DISCORD_WEBHOOK_ERRORS",
        "TWILIO_ACCOUNT_SID","TWILIO_AUTH_TOKEN","TWILIO_MESSAGING_SERVICE_SID"
    ])
    kpi_push(event="boot", data={"service": "krizzy_ops"})
    threading.Thread(target=start_watchdog, daemon=True).start()
    threading.Thread(target=start_rei_dispo, daemon=True).start()
    threading.Thread(target=start_govcon, daemon=True).start()

if __name__ == "__main__":
    on_startup()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

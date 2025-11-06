from typing import Dict

def _resp(**kwargs) -> Dict:
    return kwargs

def handle_command(text: str) -> Dict:
    if ":" not in text:
        return _resp(error="malformed", detail="use PREFIX: payload")

    prefix, payload = text.split(":", 1)
    kind = prefix.strip().upper()
    body = payload.strip()

    if kind == "STRAT":
        return _resp(PRIORITY="AUTO", ACTIONS=f"planned: {body}", KPI_TARGETS="auto", STATUS="scheduled")
    if kind == "EXEC":
        return _resp(TASK=f"execute: {body}", RESULT="queued", ETA="now", HEALTH="OK")
    if kind == "WATCH":
        return _resp(ENGINE=body or "ALL", UPTIME="unknown", ERRORS_LAST_24H=0, NEXT_CHECK="15m")
    if kind == "ADAPT":
        return _resp(POLICY_UPDATED=True, WEIGHT_CHANGES={"AUTO": "+10%"}, REVIEW_TIME="24h")
    if kind == "REPORT":
        return _resp(ENGINE_RESULTS="OK", ROI_DELTAS="+0.00", FAILURES="0 critical / 0 recoverable", NEXT_ACTION="none")

    return _resp(error="unknown_prefix", detail=kind)

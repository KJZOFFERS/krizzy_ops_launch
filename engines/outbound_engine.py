import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from utils.airtable_utils import read_records, write_record
from utils.twilio_utils import send_sms
from utils.discord_utils import post_error, post_ops

# Constants
TOTAL_DAILY_LIMIT = 100
MIN_DAYS_BETWEEN_TOUCHES = 7
TABLE_OUTBOUND_LOG = "Outbound_Log"
TABLE_LEADS_REI = "Leads_REI"
TABLE_GOVCON = "GovCon Opportunities"

# Bucket configuration: (bucket_name, daily_quota)
BUCKETS = [
    ("INBOUND", 40),
    ("WARM_MARKET", 30),
    ("COLD_LIST", 20),
    ("GOVCON_FEED", 10),
]

# Global state (protected by outbound_lock)
outbound_lock = threading.Lock()
_daily_send_count: Dict[str, int] = {bucket: 0 for bucket, _ in BUCKETS}
_last_reset_date: Optional[str] = None


def _reset_daily_counters_if_needed() -> None:
    """
    Reset daily send counters if we've crossed into a new calendar day (UTC).
    """
    global _last_reset_date, _daily_send_count
    today = datetime.utcnow().date().isoformat()
    if _last_reset_date != today:
        _last_reset_date = today
        for bucket, _ in BUCKETS:
            _daily_send_count[bucket] = 0
        post_ops(f"📅 Outbound daily counters reset for {today}")


def _get_last_touch_timestamp(phone_number: str) -> Optional[datetime]:
    """
    Query Outbound_Log for the most recent send to this phone number.
    Returns datetime or None if never contacted.
    """
    try:
        # Filter by phone number, sort by timestamp descending
        formula = f"{{phone_number}}='{phone_number}'"
        records = read_records(TABLE_OUTBOUND_LOG, filter_formula=formula)
        if not records:
            return None
        # Assume "timestamp" field is ISO8601 string
        timestamps = []
        for rec in records:
            ts_str = rec.get("fields", {}).get("timestamp")
            if ts_str:
                try:
                    timestamps.append(datetime.fromisoformat(ts_str.replace("Z", "+00:00")))
                except ValueError:
                    continue
        return max(timestamps) if timestamps else None
    except Exception as e:
        post_error(f"🚨 Outbound: failed to query last touch for {phone_number}: {e}")
        return None


def _count_touches_last_7_days(phone_number: str) -> int:
    """
    Count how many times we've contacted this phone number in the last 7 days.
    """
    try:
        cutoff = datetime.utcnow() - timedelta(days=7)
        cutoff_iso = cutoff.isoformat()
        formula = f"AND({{phone_number}}='{phone_number}', IS_AFTER({{timestamp}}, '{cutoff_iso}'))"
        records = read_records(TABLE_OUTBOUND_LOG, filter_formula=formula)
        return len(records)
    except Exception as e:
        post_error(f"🚨 Outbound: failed to count 7-day touches for {phone_number}: {e}")
        return 999  # Fail-safe: assume limit exceeded


def _is_eligible_to_send(phone_number: str) -> bool:
    """
    Check if phone_number is eligible for outbound SMS:
    - Not contacted in last MIN_DAYS_BETWEEN_TOUCHES days
    - Fewer than 3 touches in last 7 days (arbitrary limit)
    """
    last_touch = _get_last_touch_timestamp(phone_number)
    if last_touch:
        days_since = (datetime.utcnow() - last_touch).days
        if days_since < MIN_DAYS_BETWEEN_TOUCHES:
            return False

    touches_7d = _count_touches_last_7_days(phone_number)
    if touches_7d >= 3:
        return False

    return True


def _log_outbound_send(phone_number: str, bucket: str, message: str, success: bool, error_msg: Optional[str] = None) -> None:
    """
    Log outbound SMS attempt to Outbound_Log table.
    """
    try:
        fields = {
            "phone_number": phone_number,
            "bucket": bucket,
            "message": message[:500],  # Truncate long messages
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if error_msg:
            fields["error"] = error_msg[:500]
        write_record(TABLE_OUTBOUND_LOG, fields)
    except Exception as e:
        post_error(f"🚨 Outbound: failed to log send to {phone_number}: {e}")


def _send_to_bucket(bucket_name: str, quota: int) -> int:
    """
    Process outbound sends for a single bucket.
    Returns number of messages sent.
    """
    sent_count = 0
    # Placeholder: In production, fetch leads from appropriate table based on bucket
    # For now, just demonstrate structure

    # Example: INBOUND bucket pulls from Leads_REI with recent ingest
    if bucket_name == "INBOUND":
        # Placeholder logic: get recent REI leads with phone numbers
        # In real implementation, filter by Ingest_TS and presence of phone field
        pass

    # For MVP, just log that we processed the bucket
    post_ops(f"📤 Outbound {bucket_name}: processed (sent {sent_count}/{quota})")
    return sent_count


def run_outbound_engine() -> None:
    """
    Main outbound SMS engine loop.
    Runs every 5 minutes, enforces daily limits and touch rules.
    """
    while True:
        if not outbound_lock.acquire(blocking=False):
            time.sleep(300)
            continue

        try:
            _reset_daily_counters_if_needed()

            total_sent_today = sum(_daily_send_count.values())
            if total_sent_today >= TOTAL_DAILY_LIMIT:
                # Already hit daily limit
                time.sleep(300)
                continue

            for bucket_name, quota in BUCKETS:
                remaining_global = TOTAL_DAILY_LIMIT - sum(_daily_send_count.values())
                if remaining_global <= 0:
                    break

                remaining_bucket = quota - _daily_send_count[bucket_name]
                if remaining_bucket <= 0:
                    continue

                send_limit = min(remaining_bucket, remaining_global)
                sent = _send_to_bucket(bucket_name, send_limit)
                _daily_send_count[bucket_name] += sent

        except Exception as e:
            post_error(f"🔴 Outbound Engine Error: {type(e).__name__}: {e}")

        finally:
            outbound_lock.release()
            time.sleep(300)  # 5 minutes


def get_outbound_status() -> Dict[str, Any]:
    """
    Return current outbound engine status for API endpoint.
    Thread-safe.
    """
    with outbound_lock:
        return {
            "total_limit": TOTAL_DAILY_LIMIT,
            "per_bucket": {bucket: _daily_send_count[bucket] for bucket, _ in BUCKETS},
            "last_reset_date": _last_reset_date or "not_yet_run",
            "total_sent_today": sum(_daily_send_count.values()),
        }

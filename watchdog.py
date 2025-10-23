import logging
import os
import subprocess
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

from airtable_utils import fetch_all, kpi_push, safe_airtable_write
from discord_utils import post_error, post_ops

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Proxy rotation list (if available)
PROXY_LIST = os.getenv("PROXY_LIST", "").split(",") if os.getenv("PROXY_LIST") else []
current_proxy_index = 0

# Rate limiting state
rate_limit_state = {"last_429": None, "backoff_until": None, "current_delay": 1}


def rotate_proxy() -> Optional[str]:
    """Rotate to next proxy in list."""
    global current_proxy_index
    if not PROXY_LIST:
        return None

    current_proxy_index = (current_proxy_index + 1) % len(PROXY_LIST)
    proxy = PROXY_LIST[current_proxy_index].strip()
    logger.info(f"Rotated to proxy: {proxy[:20]}...")
    return proxy


def handle_rate_limit():
    """Handle 429 rate limit with exponential backoff."""
    global rate_limit_state

    now = datetime.utcnow()
    rate_limit_state["last_429"] = now
    rate_limit_state["current_delay"] = min(rate_limit_state["current_delay"] * 2, 300)  # Max 5 min
    rate_limit_state["backoff_until"] = now + timedelta(seconds=rate_limit_state["current_delay"])

    logger.warning(f"Rate limited - backing off for {rate_limit_state['current_delay']} seconds")
    post_error(f"Rate limit hit - backing off for {rate_limit_state['current_delay']}s")


def should_throttle() -> bool:
    """Check if we should throttle requests due to rate limiting."""
    if not rate_limit_state["backoff_until"]:
        return False

    return datetime.utcnow() < rate_limit_state["backoff_until"]


def restart_failed_process(process_name: str) -> bool:
    """Restart a failed process."""
    try:
        # Check if process is running
        result = subprocess.run(["pgrep", "-f", process_name], capture_output=True, text=True)

        if result.returncode != 0:  # Process not found
            logger.warning(f"Process {process_name} not running, attempting restart")

            # Restart the process
            subprocess.Popen(
                ["python3", f"{process_name}.py"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            time.sleep(2)  # Give it time to start

            # Verify it started
            result = subprocess.run(["pgrep", "-f", process_name], capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Successfully restarted {process_name}")
                post_ops(f"Restarted failed process: {process_name}")
                return True
            else:
                logger.error(f"Failed to restart {process_name}")
                post_error(f"Failed to restart process: {process_name}")
                return False

        return True  # Process is running

    except Exception as e:
        logger.error(f"Error checking/restarting {process_name}: {e}")
        post_error(f"Error managing process {process_name}: {str(e)}")
        return False


def validate_record_integrity(record: dict, table_name: str) -> list[str]:
    """
    Validate record integrity and return list of issues.

    Args:
        record: Airtable record
        table_name: Name of the table

    Returns:
        List of validation issues
    """
    issues = []
    fields = record.get("fields", {})

    # Common validations
    if not fields.get("Source_URL"):
        issues.append("Missing Source_URL")

    # Table-specific validations
    if table_name == "Leads_REI":
        if not (fields.get("Phone") or fields.get("Email")):
            issues.append("Missing contact info (Phone or Email)")

        if not fields.get("Address"):
            issues.append("Missing Address")

        # Validate phone format if present
        phone = fields.get("Phone")
        if phone and not _is_valid_phone(phone):
            issues.append("Invalid phone format")

    elif table_name == "GovCon_Opportunities":
        if not fields.get("Solicitation #"):
            issues.append("Missing Solicitation #")

        if not fields.get("Due_Date"):
            issues.append("Missing Due_Date")

        if not fields.get("Email"):
            issues.append("Missing Officer Email")

        # Check if due date is in the past
        due_date = fields.get("Due_Date")
        if due_date:
            try:
                due = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
                if due < datetime.utcnow().replace(tzinfo=due.tzinfo):
                    issues.append("Due date in past")
            except ValueError:
                issues.append("Invalid due date format")

    return issues


def _is_valid_phone(phone: str) -> bool:
    """Basic phone validation."""
    import re

    digits_only = re.sub(r'\D', '', phone)
    return len(digits_only) in [10, 11]


def clean_invalid_records(table_name: str) -> int:
    """Clean invalid records from a table."""
    try:
        records = fetch_all(table_name)
        cleaned_count = 0

        for record in records:
            issues = validate_record_integrity(record, table_name)

            if issues:
                record_id = record.get("id")
                logger.info(f"Found invalid record in {table_name}: {record_id} - {issues}")

                # Mark as invalid instead of deleting
                safe_airtable_write(
                    table_name,
                    {"Validation_Issues": ", ".join(issues), "Status": "Invalid"},
                    ["id"],
                )
                cleaned_count += 1

        return cleaned_count

    except Exception as e:
        logger.error(f"Error cleaning {table_name}: {e}")
        return 0


def monitor_system_health() -> dict[str, any]:
    """Monitor overall system health."""
    health_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "processes": {},
        "rate_limiting": {
            "active": should_throttle(),
            "last_429": rate_limit_state["last_429"].isoformat()
            if rate_limit_state["last_429"]
            else None,
            "current_delay": rate_limit_state["current_delay"],
        },
    }

    # Check critical processes
    critical_processes = ["main", "rei_dispo_engine", "govcon_subtrap_engine"]

    for process in critical_processes:
        try:
            result = subprocess.run(["pgrep", "-f", process], capture_output=True, text=True)
            health_data["processes"][process] = {
                "running": result.returncode == 0,
                "pids": result.stdout.strip().split("\n") if result.stdout.strip() else [],
            }
        except Exception as e:
            health_data["processes"][process] = {"running": False, "error": str(e)}

    return health_data


def run_watchdog() -> int:
    """
    Run comprehensive watchdog operations.

    Returns:
        Number of issues cleaned/fixed
    """
    logger.info("Starting watchdog cycle")
    total_cleaned = 0

    try:
        # Monitor system health
        health_data = monitor_system_health()
        kpi_push("watchdog_health", health_data)

        # Restart failed processes
        for process, status in health_data["processes"].items():
            if not status.get("running", False):
                if restart_failed_process(process):
                    total_cleaned += 1

        # Clean invalid records from all tables
        tables = ["Leads_REI", "GovCon_Opportunities", "Buyers"]

        for table in tables:
            try:
                cleaned = clean_invalid_records(table)
                total_cleaned += cleaned
                logger.info(f"Cleaned {cleaned} invalid records from {table}")
            except Exception as e:
                logger.error(f"Error cleaning {table}: {e}")
                post_error(f"Error cleaning {table}: {str(e)}")

        # Handle rate limiting if needed
        if should_throttle():
            logger.info("Currently throttling due to rate limits")
            post_ops("Watchdog: Currently throttling due to rate limits")

        # Rotate proxy on 403/5xx errors (if configured)
        if PROXY_LIST:
            rotate_proxy()

        # Log completion
        post_ops(f"Watchdog cycle completed - cleaned {total_cleaned} issues")
        logger.info(f"Watchdog cycle completed - cleaned {total_cleaned} issues")

        return total_cleaned

    except Exception as e:
        logger.error(f"Watchdog cycle failed: {e}")
        post_error(f"Watchdog cycle failed: {str(e)}")
        return 0


def start_continuous_monitoring():
    """Start continuous monitoring in background thread."""

    def monitor_loop():
        while True:
            try:
                run_watchdog()
                time.sleep(300)  # Run every 5 minutes
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(60)  # Wait 1 minute on error

    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    logger.info("Started continuous monitoring thread")

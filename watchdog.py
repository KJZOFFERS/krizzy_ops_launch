"""Watchdog for monitoring and restarting failed loops with throttling."""

import os
import time
import datetime
import subprocess
from typing import Dict, Any
from airtable_utils import fetch_all
from discord_utils import post_ops, post_err
import kpi


PROXY_ROTATION_ENABLED = os.getenv("PROXY_ROTATION_ENABLED", "false").lower() == "true"
CURRENT_PROXY_INDEX = 0
PROXY_LIST = os.getenv("PROXY_LIST", "").split(",")
PROXY_LIST = [p.strip() for p in PROXY_LIST if p.strip()]


def rotate_proxy() -> None:
    """Rotate to next proxy in list."""
    global CURRENT_PROXY_INDEX
    if not PROXY_ROTATION_ENABLED or not PROXY_LIST:
        return

    CURRENT_PROXY_INDEX = (CURRENT_PROXY_INDEX + 1) % len(PROXY_LIST)
    os.environ["HTTP_PROXY"] = PROXY_LIST[CURRENT_PROXY_INDEX]
    os.environ["HTTPS_PROXY"] = PROXY_LIST[CURRENT_PROXY_INDEX]
    kpi.kpi_push("proxy_rotation", {"proxy_index": CURRENT_PROXY_INDEX})


def throttle_on_429(delay_seconds: int = 60) -> None:
    """Throttle execution on rate limit."""
    post_ops(f"Throttling for {delay_seconds}s due to rate limit")
    kpi.kpi_push("throttle", {"delay_seconds": delay_seconds})
    time.sleep(delay_seconds)


def restart_process(process_name: str, command: list) -> bool:
    """
    Restart a failed process.

    Args:
        process_name: Name of the process for logging
        command: Command list to execute

    Returns:
        True if restart successful, False otherwise
    """
    try:
        post_ops(f"Restarting {process_name}")
        kpi.kpi_push("process_restart", {"process": process_name})

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300,
            check=False
        )

        if result.returncode == 0:
            post_ops(f"{process_name} restarted successfully")
            return True
        else:
            post_err(f"{process_name} restart failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        post_err(f"{process_name} restart timed out")
        return False
    except Exception as e:
        post_err(f"{process_name} restart error: {e}")
        return False


def validate_data_integrity() -> Dict[str, Any]:
    """
    Validate data integrity across tables.

    Returns:
        Dictionary with validation results
    """
    results = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "tables_checked": 0,
        "invalid_records": 0,
        "missing_required_fields": 0,
    }

    tables_to_check = [
        ("Leads_REI", ["Source_URL"]),
        ("GovCon_Opportunities", ["Solicitation_Number", "Officer_Email"]),
    ]

    for table_name, required_fields in tables_to_check:
        try:
            records = fetch_all(table_name)
            results["tables_checked"] += 1

            for record in records:
                fields = record.get("fields", {})

                for req_field in required_fields:
                    if not fields.get(req_field):
                        results["missing_required_fields"] += 1

                if table_name == "Leads_REI":
                    if not (fields.get("Phone") or fields.get("Email")):
                        results["invalid_records"] += 1

        except Exception as e:
            post_err(f"Validation error for {table_name}: {e}")
            kpi.kpi_push("error", {"source": "watchdog", "table": table_name, "error": str(e)})

    return results


def run_watchdog() -> int:
    """
    Run watchdog validation cycle.

    Returns:
        Number of invalid records found
    """
    kpi.kpi_push("cycle_start", {"engine": "watchdog"})

    results = validate_data_integrity()

    post_ops(
        f"Watchdog scan completed {results['timestamp']} | "
        f"Tables: {results['tables_checked']} | "
        f"Invalid: {results['invalid_records']} | "
        f"Missing fields: {results['missing_required_fields']}"
    )

    kpi.kpi_push("cycle_end", {"engine": "watchdog", "results": results})

    return results["invalid_records"]
